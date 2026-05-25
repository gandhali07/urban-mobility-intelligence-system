"""
Load taxi (PySpark), weather, and events (pandas) datasets.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from pyspark.sql import DataFrame, SparkSession

from src import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def create_spark_session(
    app_name: str | None = None,
    master: str = "local[*]",
    memory: str = "2g",
) -> SparkSession:
    """
    Create a SparkSession tuned for local development.
    Increase driver memory if the taxi extract is large.

    On Windows, Spark worker processes must use the same Python as this process.
    If PYSPARK_PYTHON is unset, `python` can resolve to the Store stub and workers fail with
    "Python was not found" / "Python worker failed to connect back".
    """
    py = sys.executable
    os.environ.setdefault("PYSPARK_PYTHON", py)
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", py)
    logger.info("Spark will use Python: %s", py)

    name = app_name or config.SPARK_APP_NAME
    logger.info("Starting Spark session: app=%s master=%s", name, master)
    spark = (
        SparkSession.builder.appName(name)
        .master(master)
        .config("spark.driver.memory", memory)
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def load_taxi_spark(
    spark: SparkSession,
    path: Path | str | None = None,
    file_format: str | None = None,
    header: bool = True,
    infer_schema: bool = True,
) -> DataFrame:
    """
    Load taxi trips with PySpark.

    For TLC data, columns often include: tpep_pickup_datetime, tpep_dropoff_datetime,
    passenger_count, trip_distance, pickup/dropoff lat/lon, fare_amount, etc.
    This loader accepts CSV or Parquet; set file_format accordingly.
    """
    p = Path(path) if path else config.taxi_csv_path()
    if not p.exists():
        raise FileNotFoundError(
            f"Taxi data not found at {p}.\n"
            "Add a TLC-style Yellow/Green trip file to data/raw/ (CSV or Parquet), e.g. "
            f"{config.TAXI_CSV_NAME!r} or any *yellow* / *taxi* / *.parquet file."
        )
    if file_format is None:
        suff = p.suffix.lower()
        file_format = "parquet" if suff in (".parquet", ".parq") else "csv"
    logger.info("Loading taxi data from %s (%s)", p, file_format)
    reader = spark.read
    if file_format.lower() == "csv":
        df = reader.option("header", str(header).lower()).option(
            "inferSchema", str(infer_schema).lower()
        ).csv(str(p))
    elif file_format.lower() == "parquet":
        df = reader.parquet(str(p))
    else:
        raise ValueError(f"Unsupported format: {file_format}")
    logger.info("Taxi rows (Spark): %s", df.count())
    return df


def load_weather_pandas(path: Path | str | None = None) -> pd.DataFrame:
    """Load NYC weather: Kaggle wide-format folder (nyc_weather/) or a single long CSV."""
    if path is None and config.weather_csv_path().is_file():
        p = config.weather_csv_path()
        logger.info("Loading weather from %s", p)
        df = pd.read_csv(p, low_memory=False)
        logger.info("Weather shape: %s", df.shape)
        return df
    if path is None and config.nyc_weather_dir().is_dir():
        tfp = config.nyc_weather_dir() / "temperature.csv"
        if tfp.is_file():
            from src.weather_loader import load_nyc_weather_from_kaggle_folder

            df = load_nyc_weather_from_kaggle_folder(
                config.nyc_weather_dir(), city=config.NYC_WEATHER_CITY
            )
            if not df.empty:
                return df
    p = Path(path) if path else config.weather_csv_path()
    if not p.exists():
        logger.warning("Weather file missing at %s — returning empty DataFrame.", p)
        return pd.DataFrame()
    logger.info("Loading weather from %s", p)
    df = pd.read_csv(p, low_memory=False)
    logger.info("Weather shape: %s", df.shape)
    return df


def load_events_pandas(path: Path | str | None = None) -> pd.DataFrame:
    """Load NYC events (date, lat, lon, name, category, ...)."""
    p = Path(path) if path else config.events_csv_path()
    if not p.exists():
        logger.warning("Events file missing at %s — returning empty DataFrame.", p)
        return pd.DataFrame()
    logger.info("Loading events from %s", p)
    try:
        df = pd.read_csv(p, low_memory=False, encoding="utf-8", on_bad_lines="skip")
    except Exception:
        df = pd.read_csv(p, encoding="utf-8")
    df.columns = [str(c).strip().strip('"') for c in df.columns]
    logger.info("Events shape: %s", df.shape)
    return df
