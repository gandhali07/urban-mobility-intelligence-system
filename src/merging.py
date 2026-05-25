"""
Merge taxi, weather, and events using temporal (hour, day) keys.
Uses PySpark for the taxi ↔ weather join so it scales; events join is daily.
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


def _weather_time_column(weather_pdf: pd.DataFrame) -> str:
    for c in ("time", "datetime", "date_time", "timestamp"):
        if c in weather_pdf.columns:
            return c
    raise ValueError(
        "Weather DataFrame needs a time column named one of: time, datetime, date_time, timestamp"
    )


def merge_taxi_weather_events_spark(
    taxi_df: DataFrame,
    weather_pdf: pd.DataFrame,
    events_pdf: pd.DataFrame,
    spark: SparkSession,
    weather_time_col: Optional[str] = None,
    event_date_col: str = "event_date",
) -> DataFrame:
    """
    Left-join taxi trips to hourly weather and daily event counts.

    - Weather: join on hour bucket of pickup_ts.
    - Events: join on calendar day; adds event_count (trips on days with more events).
    """
    logger.info("Merging taxi with weather (Spark)...")
    if weather_pdf.empty:
        logger.warning("Weather empty — skipping weather join.")
        merged = taxi_df.withColumn("weather_join_missing", F.lit(1))
    else:
        w = weather_pdf.copy()
        tcol = weather_time_col or _weather_time_column(w)
        w["_weather_hour"] = pd.to_datetime(w[tcol], errors="coerce").dt.floor("h")
        w = w.dropna(subset=["_weather_hour"])
        # Drop duplicate time column name if present in taxi
        drop_cols = [c for c in w.columns if c in taxi_df.columns and c != "_weather_hour"]
        for c in drop_cols:
            w = w.rename(columns={c: f"weather__{c}"})
        weather_sdf = spark.createDataFrame(w)
        taxi_h = taxi_df.withColumn("_pickup_hour", F.date_trunc("hour", F.col("pickup_ts")))
        merged = taxi_h.join(
            weather_sdf,
            taxi_h._pickup_hour == weather_sdf._weather_hour,
            how="left",
        )
        merged = merged.drop("_pickup_hour", "_weather_hour")

    merged = merged.withColumn("trip_day", F.to_date(F.col("pickup_ts")))

    if events_pdf.empty:
        logger.warning("Events empty — event_count set to 0.")
        merged = merged.withColumn("event_count", F.lit(0))
    else:
        e = events_pdf.copy()
        if event_date_col not in e.columns:
            raise ValueError(f"Events DataFrame must contain '{event_date_col}'")
        e["_event_day"] = pd.to_datetime(e[event_date_col], errors="coerce").dt.normalize()
        e = e.dropna(subset=["_event_day"])
        daily = e.groupby("_event_day").size().reset_index(name="event_count")
        daily["_event_day"] = pd.to_datetime(daily["_event_day"]).dt.normalize()
        events_sdf = spark.createDataFrame(daily)
        events_sdf = events_sdf.withColumn(
            "_event_day", F.to_date(F.col("_event_day"))
        )
        merged = merged.join(
            events_sdf,
            merged.trip_day == events_sdf._event_day,
            how="left",
        ).drop("_event_day")
        merged = merged.fillna({"event_count": 0})

    n = merged.count()
    logger.info("Merged Spark DataFrame rows: %s", n)
    return merged


def merged_spark_to_pandas(
    merged_df: DataFrame,
    max_rows: Optional[int] = None,
) -> pd.DataFrame:
    """
    Materialize merged Spark DataFrame to pandas (use max_rows for local dev).
    For very large data, write to Parquet and train on a sample.
    """
    if max_rows is not None:
        logger.info("Collecting up to %s rows to pandas...", max_rows)
        pdf = merged_df.limit(max_rows).toPandas()
    else:
        logger.info("Collecting full merged DataFrame to pandas (may be heavy)...")
        pdf = merged_df.toPandas()
    logger.info("Pandas shape after merge: %s", pdf.shape)
    return pdf
