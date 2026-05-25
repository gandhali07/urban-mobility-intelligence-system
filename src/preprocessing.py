"""
Preprocess taxi (Spark), weather, and events (pandas).
"""
from __future__ import annotations

import hashlib
import logging
import math
import time
import pandas as pd
import requests
from pyspark.sql import DataFrame, functions as F
from pyspark.sql.types import DoubleType

from src import config

logger = logging.getLogger(__name__)

# NYC borough centroids (approximate) for events without exact street geocodes
NYC_BOROUGH_CENTROIDS: dict[str, tuple[float, float]] = {
    "manhattan": (40.7831, -73.9712),
    "brooklyn": (40.6782, -73.9442),
    "queens": (40.7282, -73.7949),
    "bronx": (40.8448, -73.8648),
    "staten island": (40.5795, -74.1502),
    "staten": (40.5795, -74.1502),
}
DEFAULT_NYC_POINT: tuple[float, float] = (40.7128, -74.0060)

# Flexible column name mapping for Yellow Taxi–style CSVs
DEFAULT_TAXI_COLUMN_ALIASES = {
    "tpep_pickup_datetime": "pickup_ts",
    "tpep_dropoff_datetime": "dropoff_ts",
    "pickup_latitude": "pickup_lat",
    "pickup_longitude": "pickup_lon",
    "dropoff_latitude": "dropoff_lat",
    "dropoff_longitude": "dropoff_lon",
}


def normalize_taxi_columns(df: DataFrame, aliases: dict | None = None) -> DataFrame:
    """Rename known TLC column names to internal names."""
    mapping = aliases or DEFAULT_TAXI_COLUMN_ALIASES
    for old, new in mapping.items():
        if old in df.columns:
            df = df.withColumnRenamed(old, new)
    return df


def filter_nyc_bbox(df: DataFrame) -> DataFrame:
    """Keep rows with pickup coordinates inside NYC bounding box."""
    lat_col = "pickup_lat" if "pickup_lat" in df.columns else None
    lon_col = "pickup_lon" if "pickup_lon" in df.columns else None
    if not lat_col or not lon_col:
        logger.warning("pickup_lat/pickup_lon not found — skipping bbox filter.")
        return df
    return df.filter(
        (F.col(lat_col).between(config.NYC_LAT_MIN, config.NYC_LAT_MAX))
        & (F.col(lon_col).between(config.NYC_LON_MIN, config.NYC_LON_MAX))
    )


def add_trip_duration_seconds(df: DataFrame) -> DataFrame:
    """Compute trip duration in seconds if pickup/dropoff timestamps exist."""
    if "pickup_ts" not in df.columns or "dropoff_ts" not in df.columns:
        logger.warning("pickup_ts/dropoff_ts missing — cannot compute duration.")
        return df.withColumn("trip_duration_sec", F.lit(None).cast(DoubleType()))
    out = df.withColumn(
        "trip_duration_sec",
        F.unix_timestamp("dropoff_ts") - F.unix_timestamp("pickup_ts"),
    )
    return out.filter(
        (F.col("trip_duration_sec") > 0) & (F.col("trip_duration_sec") < 24 * 3600)
    )


def cast_taxi_timestamps(df: DataFrame) -> DataFrame:
    """Cast pickup/dropoff to timestamp if they are strings."""
    for c in ("pickup_ts", "dropoff_ts"):
        if c in df.columns:
            df = df.withColumn(c, F.to_timestamp(F.col(c)))
    return df


def preprocess_taxi_spark(df: DataFrame) -> DataFrame:
    """Full taxi preprocessing chain on Spark."""
    logger.info("Preprocessing taxi (Spark)...")
    df = normalize_taxi_columns(df)
    df = cast_taxi_timestamps(df)
    df = filter_nyc_bbox(df)
    df = add_trip_duration_seconds(df)
    if "trip_distance" in df.columns:
        df = df.filter(
            (F.col("trip_distance").isNotNull()) & (F.col("trip_distance") >= 0)
        )
    else:
        logger.warning("Column trip_distance not found — skipping distance filter.")
    n = df.count()
    logger.info("Taxi rows after preprocessing: %s", n)
    return df


def _detect_time_column(df: pd.DataFrame) -> str | None:
    for c in ("time", "datetime", "date_time", "timestamp"):
        if c in df.columns:
            return c
    return None


def preprocess_weather_df(df: pd.DataFrame, time_col: str | None = None) -> pd.DataFrame:
    """Parse weather time column and sort."""
    if df.empty:
        return df
    out = df.copy()
    tcol = time_col if time_col and time_col in out.columns else _detect_time_column(out)
    if tcol is None:
        logger.warning("Weather has no time/datetime column — leaving as-is.")
    else:
        out[tcol] = pd.to_datetime(out[tcol], errors="coerce")
        out = out.dropna(subset=[tcol])
        if tcol != "time" and "time" not in out.columns:
            out = out.rename(columns={tcol: "time"})
    numeric_cols = out.select_dtypes(include=["float64", "int64", "float32", "int32"]).columns
    if len(numeric_cols) > 0:
        out[numeric_cols] = out[numeric_cols].fillna(out[numeric_cols].median(numeric_only=True))
    logger.info("Weather preprocessed, shape %s", out.shape)
    return out


def _borough_to_lat_lon(borough: str | float) -> tuple[float, float]:
    b = str(borough).lower().strip()
    for key, (la, lo) in NYC_BOROUGH_CENTROIDS.items():
        if key in b or b in key:
            return la, lo
    return DEFAULT_NYC_POINT


def _event_jitter(seed_value: str, max_deg: float = 0.03) -> tuple[float, float]:
    """
    Deterministic circular jitter so fallback points do not form rectangular blocks.
    """
    digest = hashlib.md5(seed_value.encode("utf-8")).hexdigest()
    angle = (int(digest[:8], 16) / 0xFFFFFFFF) * 2 * math.pi
    radius = math.sqrt(int(digest[8:16], 16) / 0xFFFFFFFF) * max_deg
    return radius * math.cos(angle), radius * math.sin(angle)


def _extract_location_query(raw_location: str) -> str:
    """Convert Event Location text into a geocoding-friendly place query."""
    txt = str(raw_location).strip()
    if not txt:
        return ""
    primary = txt.split(",")[0].strip()
    main_name = primary.split(":")[0].strip()
    return main_name


def _load_geocode_cache() -> pd.DataFrame:
    cache_path = config.GEOCACHE_DIR / "events_location_geocode_cache.csv"
    if cache_path.exists():
        try:
            return pd.read_csv(cache_path)
        except Exception:
            return pd.DataFrame(columns=["query", "lat", "lon"])
    return pd.DataFrame(columns=["query", "lat", "lon"])


def _save_geocode_cache(df: pd.DataFrame) -> None:
    cache_path = config.GEOCACHE_DIR / "events_location_geocode_cache.csv"
    df.drop_duplicates(subset=["query"], keep="last").to_csv(cache_path, index=False)


def _geocode_query_nominatim(query: str, borough: str | None = None) -> tuple[float | None, float | None]:
    """
    Geocode one location via Nominatim.
    Uses a short timeout and returns None on failure.
    """
    q_parts = [query]
    if borough:
        q_parts.append(str(borough))
    q_parts.extend(["New York", "NY", "USA"])
    q = ", ".join([p for p in q_parts if p])
    url = "https://nominatim.openstreetmap.org/search"
    try:
        resp = requests.get(
            url,
            params={"q": q, "format": "json", "limit": 1},
            headers={"User-Agent": "urban-mobility-intel/1.0"},
            timeout=8,
        )
        resp.raise_for_status()
        arr = resp.json()
        if not arr:
            return None, None
        return float(arr[0]["lat"]), float(arr[0]["lon"])
    except Exception:
        return None, None


def _enrich_event_coords_with_geocoding(df: pd.DataFrame, max_new_queries: int = 120) -> pd.DataFrame:
    """
    Try to geocode unique event location names and cache results.
    This improves map realism when raw events file has no lat/lon columns.
    """
    out = df.copy()
    out["_loc_query"] = out.get("Event Location", "").astype(str).map(_extract_location_query)
    out["_borough"] = out.get("Event Borough", "").astype(str)

    cache = _load_geocode_cache()
    if "query" not in cache.columns:
        cache = pd.DataFrame(columns=["query", "lat", "lon"])

    known = {
        str(r["query"]): (float(r["lat"]), float(r["lon"]))
        for _, r in cache.dropna(subset=["query", "lat", "lon"]).iterrows()
    }

    unique_queries = [q for q in out["_loc_query"].dropna().unique().tolist() if str(q).strip()]
    missing = [q for q in unique_queries if q not in known]

    # Avoid very slow first runs; fill cache progressively.
    missing = missing[:max_new_queries]
    if missing:
        logger.info("Geocoding %s new event locations...", len(missing))

    new_rows: list[dict[str, float | str]] = []
    borough_lookup = (
        out[["_loc_query", "_borough"]]
        .dropna(subset=["_loc_query"])
        .drop_duplicates("_loc_query")
        .set_index("_loc_query")["_borough"]
        .to_dict()
    )

    for q in missing:
        lat, lon = _geocode_query_nominatim(str(q), borough=str(borough_lookup.get(q, "")))
        if lat is not None and lon is not None:
            known[str(q)] = (lat, lon)
            new_rows.append({"query": str(q), "lat": lat, "lon": lon})
        time.sleep(1.0)

    if new_rows:
        cache = pd.concat([cache, pd.DataFrame(new_rows)], ignore_index=True)
        _save_geocode_cache(cache)

    out["lat"] = out["_loc_query"].map(lambda q: known.get(str(q), (None, None))[0])
    out["lon"] = out["_loc_query"].map(lambda q: known.get(str(q), (None, None))[1])
    return out


def preprocess_events_df(
    df: pd.DataFrame,
    date_col: str = "event_date",
    lat_col: str = "lat",
    lon_col: str = "lon",
) -> pd.DataFrame:
    """Parse event dates; keep rows with lat/lon or NYC Parks–style borough locations."""
    if df.empty:
        return df
    out = df.copy()
    lower_event_mapping = {
        "event_id": "Event ID",
        "event_name": "Event Name",
        "start_date_time": "Start Date/Time",
        "end_date_time": "End Date/Time",
        "event_agency": "Event Agency",
        "event_type": "Event Type",
        "event_borough": "Event Borough",
        "event_location": "Event Location",
        "event_street_side": "Event Street Side",
        "street_closure_type": "Street Closure Type",
        "community_board": "Community Board",
        "police_precinct": "Police Precinct",
    }
    out = out.rename(
        columns={
            old: new
            for old, new in lower_event_mapping.items()
            if old in out.columns and new not in out.columns
        }
    )

    nyc_parks = (
        "Start Date/Time" in out.columns
        and "Event Name" in out.columns
        and "Event Borough" in out.columns
    )
    if nyc_parks:
        out["event_date"] = pd.to_datetime(out["Start Date/Time"], errors="coerce")
        out = out.dropna(subset=["event_date"])
        out["name"] = out["Event Name"].astype(str)
        out["category"] = out.get("Event Type", "event")
        out = _enrich_event_coords_with_geocoding(out)

        # Fallback only when geocoding is unavailable for a row.
        missing_mask = out["lat"].isna() | out["lon"].isna()
        if missing_mask.any():
            coords = out.loc[missing_mask, "Event Borough"].map(
                lambda x: _borough_to_lat_lon(str(x) if pd.notna(x) else "")
            )
            out.loc[missing_mask, "lat"] = coords.map(lambda t: t[0]).astype(float)
            out.loc[missing_mask, "lon"] = coords.map(lambda t: t[1]).astype(float)

            if "Event ID" in out.columns:
                seed_series = out.loc[missing_mask, "Event ID"].astype(str)
            else:
                seed_series = (
                    out.loc[missing_mask].get("Event Name", "").astype(str)
                    + "|"
                    + out.loc[missing_mask].get("Event Location", "").astype(str)
                    + "|"
                    + out.loc[missing_mask, "event_date"].astype(str)
                )
            jitter = seed_series.map(_event_jitter)
            out.loc[missing_mask, "lat"] = out.loc[missing_mask, "lat"].astype(float) + jitter.map(
                lambda t: t[0]
            )
            out.loc[missing_mask, "lon"] = out.loc[missing_mask, "lon"].astype(float) + jitter.map(
                lambda t: t[1]
            )
    else:
        if date_col in out.columns:
            out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
            out = out.dropna(subset=[date_col])
        for c in (lat_col, lon_col):
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors="coerce")
        if lat_col in out.columns and lon_col in out.columns:
            out = out.dropna(subset=[lat_col, lon_col])
    out = out.dropna(subset=["lat", "lon"]) if "lat" in out.columns and "lon" in out.columns else out
    logger.info("Events preprocessed, shape %s", out.shape)
    return out
