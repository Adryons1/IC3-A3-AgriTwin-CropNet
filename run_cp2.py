#!/usr/bin/env python3
"""IC3 / CP2 / A3: first real CropNet-USDA yield-only experiment.

County × year, Iowa maize, pilot 30 counties, 2017–2022.
2022 is held out; all predictors derive only from preceding annual yields.
IMPORTANT: S2 / WRF-HRRR are NOT part of this first experiment.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

FEATURES = ['lag1', 'lag2', 'history_mean', 'history_std', 'last3_mean', 'yearly_change']


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for fips, county in df.groupby('FIPS', sort=True):
        county = county.sort_values('year')
        for _, cur in county.iterrows():
            t = int(cur.year)
            hist = county[county.year < t]['yield_bu_ac'].to_numpy(dtype=float)
            if len(hist) < 2:
                continue
            rows.append({
                'FIPS': str(fips), 'county_name': cur.county_name, 'year': t,
                'yield_bu_ac': float(cur.yield_bu_ac),
                'lag1': float(hist[-1]), 'lag2': float(hist[-2]),
                'history_mean': float(np.mean(hist)),
                'history_std': float(np.std(hist, ddof=0)),
                'last3_mean': float(np.mean(hist[-3:])),
                'yearly_change': float(hist[-1] - hist[-2]),
            })
    return pd.DataFrame(rows).sort_values(['year', 'FIPS']).reset_index(drop=True)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {'MAE_BU_AC': round(float(mean_absolute_error(y_true, y_pred)), 3),
            'RMSE_BU_AC': round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 3)}


def execute(source: Path, out_dir: Path, show=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(source, dtype={'FIPS': str, 'state_ansi': str, 'county_ansi': str})
    expected = set(range(2017, 2023))
    assert set(df.year.unique()) == expected, 'Expect years 2017-2022'
    assert df.FIPS.nunique() == 30 and len(df) == 30 * 6, 'Expect exactly 30 complete counties'
    assert not df[['FIPS','year']].duplicated().any(), 'No duplicate county-years'
    assert df.yield_bu_ac.notna().all(), 'No missing yields'
    assert (df.yield_bu_ac > 0).all(), 'All yields must be positive'
    features = build_features(df)
    train = features[features.year <= 2021].copy()  # only 2019-2021 labeled examples
    test = features[features.year == 2022].copy()
    assert sorted(train.year.unique().tolist()) == [2019, 2020, 2021]
    assert sorted(test.year.unique().tolist()) == [2022] and len(test)==30
    assert set(test.FIPS) == set(train.FIPS)

    model = RandomForestRegressor(n_estimators=300, max_depth=5, min_samples_leaf=3, random_state=42, n_jobs=1)
    model.fit(train[FEATURES], train.yield_bu_ac)
    predictions = {
        'Climatologie locala (media 2017-2021)': test.history_mean.to_numpy(),
        'Persistenta (randament 2021)': test.lag1.to_numpy(),
        'Random Forest (istoric USDA)': model.predict(test[FEATURES])
    }
    metrics = []
    pred_df = test[['FIPS','county_name','year','yield_bu_ac']].copy()
    for name, values in predictions.items():
        pred_df[name] = np.round(values,3)
        m = compute_metrics(test.yield_bu_ac.to_numpy(), values)
        metrics.append({'model':name, **m, 'n_test':len(test), 'test_year':2022})
    metr = pd.DataFrame(metrics)
    metr.to_csv(out_dir/'metrics_2022.csv',index=False)
    pred_df.to_csv(out_dir/'predictions_2022.csv',index=False)
    features.to_csv(out_dir/'feature_matrix_2019_2022.csv',index=False)
    (out_dir/'protocol.json').write_text(json.dumps({
        'project':'IC3-A3-CP2', 'crop':'corn', 'geography':'Iowa, 30 explicitly enumerated counties',
        'target':'USDA annual corn yield in bushels/acre (BU/AC)',
        'unit':'county-year','source':'CropNet USDA Corn County CSV (2017-2022)',
        'holdout_year':2022, 'base_history_years':[2017,2018,2019,2020,2021],
        'random_forest_training_years':[2019,2020,2021],
        'n_train_rf':len(train),'n_test':len(test), 'seed':42,
        'features':FEATURES,
        'no_target_leakage':'All features for a target year use yields strictly before that year',
        'multimodal_status':'Sentinel-2 and WRF-HRRR NOT downloaded / included; August 31 restriction to be enforced when added',
        'protocol_note':'Temporal holdout 2022; this is one year-fold, not a complete LOYO.',
        'limitations':'Nonrandom 30-county pilot, no same-season predictors; no in-season forecasting claim.'
    }, ensure_ascii=False, indent=2), encoding='utf-8')

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12})
    fig, ax = plt.subplots(figsize=(10.4, 4.6))
    xx=np.arange(len(metr)); width=.32
    ax.bar(xx - width/2, metr.MAE_BU_AC, width, label='MAE', color='#C7834A')
    ax.bar(xx + width/2, metr.RMSE_BU_AC, width, label='RMSE', color='#1A3853')
    ax.set_xticks(xx, ['Climatologie\nlocală','Persistență\n2021','Random Forest\n(istoric USDA)'])
    ax.set_ylabel('Eroare (BU/AC)'); ax.grid(axis='y',alpha=.17);ax.set_axisbelow(True)
    ax.legend(frameon=False,ncol=2,loc='upper left')
    ax.spines[['top','right']].set_visible(False)
    for bars in ax.containers:
        ax.bar_label(bars,fmt='%.1f',padding=4,fontsize=11)
    fig.tight_layout()
    fig.savefig(out_dir/'comparison_2022.png',dpi=180,bbox_inches='tight')
    plt.close(fig)
    print('DATA:', len(df), 'county-years |', df.FIPS.nunique(), 'counties | 2017-2022')
    print('RF train=',len(train),'test=',len(test),'heldout year=2022')
    print(metr.to_string(index=False))
    if show:
        print(pred_df.head().to_string(index=False))
    return metr

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=Path(__file__).parent/'data/usda_corn_iowa_pilot30_2017_2022.csv')
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'outputs')
    args=parser.parse_args();execute(args.input,args.output)
