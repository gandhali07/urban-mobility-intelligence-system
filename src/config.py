"""
Central paths and constants for the Urban Mobility Intelligence pipeline.
Adjust RAW_DATA_DIR and file names to match your downloaded datasets.
"""
from pathlib import Path

# Project root (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MAPS_DIR = OUTPUTS_DIR / "maps"
MODELS_DIR = OUTPUTS_DIR / "models"
FIGURES_DIR = OUTPUTS_DIR / "figures"
GEOCACHE_DIR = OUTPUTS_DIR / "geocache"

# Expected input filenames (place files under data/raw/)
# Taxi: set this file name, OR place a *parquet / *taxi* / *yellow* / *trip* CSV in data/raw/ (see resolve_taxi_path)
TAXI_CSV_NAME = "yellow_taxi_sample.csv"  # TLC-style CSV or your extract name
# Single-file weather (optional) if you do not use data/raw/nyc_weather/ folder
WEATHER_CSV_NAME = "nyc_weather_2023_02.csv"
EVENTS_CSV_NAME = "nyc_events_2023_02.csv"
# Kaggle wide-format weather folder (data/raw/nyc_weather/temperature.csv, etc.)
NYC_WEATHER_DIR_NAME = "nyc_weather"
NYC_WEATHER_CITY = "New York"  # column name inside those CSVs

# NYC approximate bounding box (filter bad GPS rows)
NYC_LAT_MIN, NYC_LAT_MAX = 40.50, 40.92
NYC_LON_MIN, NYC_LON_MAX = -74.26, -73.70

# Spark
SPARK_APP_NAME = "UrbanMobilityIntelligence"

# Random seed for reproducibility
RANDOM_STATE = 42


def ensure_output_dirs() -> None:
    """Create output subfolders if they do not exist."""
    for d in (
        OUTPUTS_DIR,
        MAPS_DIR,
        MODELS_DIR,
        FIGURES_DIR,
        PROCESSED_DATA_DIR,
        GEOCACHE_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


def taxi_csv_path() -> Path:
    return resolve_taxi_path()


def weather_csv_path() -> Path:
    return RAW_DATA_DIR / WEATHER_CSV_NAME


def events_csv_path() -> Path:
    return RAW_DATA_DIR / EVENTS_CSV_NAME


def nyc_weather_dir() -> Path:
    return RAW_DATA_DIR / NYC_WEATHER_DIR_NAME


def resolve_taxi_path() -> Path:
    """
    Pick a taxi trip file in data/raw/:
    1) TAXI_CSV_NAME if it exists
    2) any .parquet / .parq in data/raw/ (not under subfolders except user may add)
    3) any CSV whose name suggests TLC/yellow/taxi/trip
    4) any top-level .csv in data/raw/ except the events file
    """
    preferred = RAW_DATA_DIR / TAXI_CSV_NAME
    if preferred.is_file():
        return preferred
    for pat in ("*.parquet", "*.parq"):
        for p in sorted(RAW_DATA_DIR.glob(pat)):
            if p.is_file():
                return p
    for key in ("yellow", "green", "taxi", "trip", "tlc", "nyctaxi"):
        for p in sorted(RAW_DATA_DIR.glob(f"*{key}*.csv")):
            if p.is_file() and p.name.lower() != EVENTS_CSV_NAME.lower():
                return p
    for p in sorted(RAW_DATA_DIR.glob("*.csv")):
        if p.name.lower() == EVENTS_CSV_NAME.lower():
            continue
        if p.is_file():
            return p
    return preferred
