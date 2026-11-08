# IC3 / A3 / CP2 — AgriTwin: randament porumb, Iowa

**Autor:** Dumitru Florin-Adrian  
**Tema:** A3 — Comitat agricol (CropNet): randament, leave-one-year-out  
**Checkpoint:** CP2 — Reprezentare, baseline și protocol

## Ce este deja rulat

Primul experiment **pe randamente USDA reale** din CropNet: 30 de comitate din Iowa × 6 ani (2017–2022), 180 de înregistrări `comitat × an`. Am extras un pilot fix cu 30 de comitate care au toate cele 6 etichete și am păstrat anul **2022 separat pentru test**.

### Reprezentări de comparat

- **A (reprezentare aleasă pentru baseline-ul CP2):** vector numeric de istoric al randamentului `[lag1, lag2, media anilor anteriori, abaterea standard istorică, media ultimilor 3 ani, diferența dintre ultimii 2 ani]`. Unitatea: `comitat × an`, randament în `BU/AC`.
- **B (alternativă simplă):** un singur număr pe comitat: **media randamentelor din anii anteriori** (climatologie locală). Pentru control mai raportăm **persistența**: valoarea randamentului din anul precedent.

Modelul cu reprezentarea A este `RandomForestRegressor`, seed=42, 300 de arbori, `max_depth=5`, `min_samples_leaf=3`. Este antrenat pe exemple țintă 2019–2021, deoarece din 2019 există cel puțin 2 ani anteriori pentru a calcula toate trăsăturile. Metodele baseline nu necesită antrenare. Evaluarea finală este pe **30 de comitate din 2022**, fără să folosim randamentul din 2022 la construirea predictorilor.

**Important:** acest CP2 este în prezent un **baseline USDA bazat exclusiv pe istoricul randamentului**, nu predicția multimodală finală. **Nu au fost procesate Sentinel-2 sau WRF-HRRR**. Restricția „date până la 31 august” va trebui verificată explicit când adăugăm sursele satelitare/meteo. Nu afirmăm că proiectul complet produce deja predicții din vreme și satelit.

## Protocol și limitări

- **Split temporal:** istoricul 2017–2021 pentru testarea anului 2022. Random Forest primește exemple țintă din 2019–2021; 2022 rămâne complet neobservat ca țintă în antrenare. Acesta este **un singur fold temporal**, **nu LOYO complet**. Un experiment LOYO cu fiecare an separat se face după validarea datelor multimodale, cu atenție la posibila folosire a valorilor din viitor.
- Datele de antrenare nu conțin caracteristici calculate din anul-țintă sau din ani ulteriori acestuia.
- **Metrici:** MAE și RMSE în `BU/AC`. Unitățile sunt aceleași ca pentru ținta USDA.
- **Limite:** doar 30 de comitate alese pentru continuitatea seriilor; selecția nu este aleatoare/reprezentativă; perioada scurtă și lipsa datelor satelitare/meteo limitează generalizarea și prognoza sezonieră.

## Reproducere

În terminal, în folderul proiectului:

```bash
python -m pip install -r requirements.txt
python run_cp2.py
```

Dacă execuția reușește, `outputs/` conține:

- `metrics_2022.csv` — MAE/RMSE pentru 3 metode
- `predictions_2022.csv` — valorile reale și cele prezise, per comitat
- `feature_matrix_2019_2022.csv` — descriptori strict din anii anteriori
- `comparison_2022.png` — graficul din slide-ul 2
- `protocol.json` — parametrii de reproducere

## Proveniența datelor

Datele folosite sunt o transcriere verificabilă a coloanei `YIELD, MEASURED IN BU / ACRE` din cele 6 fișiere anuale CropNet pentru cultura `Corn`, comitate din Iowa (`state_ansi = 19`). Identificatorii comitatelor sunt `19` + codul din 3 cifre al comitatului. Am păstrat numele, FIPS, anul și randamentul. Nu sunt generate sintetic.

- Dataset: <https://huggingface.co/datasets/CropNet/CropNet>
- Folder sursă: <https://huggingface.co/datasets/CropNet/CropNet/tree/main/USDA%20Crop%20Dataset/Corn>
- Repository upstream CropNet: <https://github.com/fudonglin/CropNet>
- Articol original: Lin et al., *An Open and Large-Scale Dataset for Multi-Modal Climate Change-aware Crop Yield Predictions*, KDD 2024, <https://arxiv.org/abs/2406.06081>

**Notă despre licență:** verifică termenii licenței la sursă înainte de redistribuirea datelor. Nu confunda repository-ul upstream al autorilor cu repository-ul *tău* pentru CP2.

## Ce trebuie făcut pentru predare

1. Creează un repository GitHub, de exemplu `ic3-a3-cp2`, și încarcă `run_cp2.py`, `data/`, `outputs/`, `requirements.txt`, `README.md`.
2. În PowerPointul CP2, la slide-ul 2, înlocuiește **`REPO: [ADAUGA LINKUL TAU]`** cu linkul efectiv GitHub (nu doar cu GitHub CropNet al autorilor).
3. Exportă din PowerPoint varianta actualizată în PDF și încarc-o pe Moodle înainte de termenul-limită.

## Plan CP3

- Aliniere FIPS × an pentru setul pilot cu weather WRF-HRRR + NDVI Sentinel-2, **până la 31 august** în fiecare an.
- Audit de lipsuri S2/HRRR pe fiecare comitat-an; imputare numai din train.
- Repetarea evaluării 2022 cu `RF(weather)` versus `RF(weather+NDVI)` și baselines istorice, apoi extindere la protocolul LOYO/rolling temporal fără leakage.
