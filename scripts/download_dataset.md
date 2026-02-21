# Download Student Mental Health dataset

This file shows two ways to get the Kaggle dataset into this repo under `data/`.

1) Using the Kaggle CLI (recommended)

- Install and configure once:

```powershell
pip install kaggle
# Place your kaggle.json at %USERPROFILE%\\.kaggle\\kaggle.json (Windows)
```

- Download the CSV and unzip into `data/`:

```powershell
kaggle datasets download -d shariful07/student-mental-health-data-analysis -f StudentMentalHealth.csv -p data --unzip
```

2) Manual download

- Open the dataset page in your browser and download the CSV. Place it at `data/StudentMentalHealth.csv`.

After placing the CSV in `data/`, run the preprocessing + training script:

```powershell
python scripts/preprocess_and_train.py --csv data/StudentMentalHealth.csv
```
