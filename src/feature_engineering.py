"""
Feature engineering for modeling: time, distance, weather, events, congestion proxies.
"""
from __future__ import annotations

import logging
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

AIRPORT_LOCATION_IDS = {1, 132, 138}
UNKNOWN_LOCATION_IDS = {264, 265}


def add_time_features(df: pd.DataFrame, pickup_col: str = "pickup_ts") -> pd.DataFrame:
    """Hour, day of week, month from pickup timestamp."""
    out = df.copy()
    if pickup_col not in out.columns:
        logger.warning("Missing %s — skipping time features.", pickup_col)
        return out
    ts = pd.to_datetime(out[pickup_col], errors="coerce")
    out["hour"] = ts.dt.hour
    out["dow"] = ts.dt.dayofweek
    out["month"] = ts.dt.month
    return out


def _numeric_bin(series: pd.Series, bins: list[float]) -> pd.Series:
    """Return stable numeric bins with NaN preserved."""
    values = pd.to_numeric(series, errors="coerce")
    return pd.cut(values, bins=bins, labels=False, include_lowest=True).astype("float")


def add_domain_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add practical pre-trip features that a dispatcher/user could know before pickup.

    These make the model easier to explain: rush hour, weekend, airport trip,
    weather flags, and simple bucketed versions of distance/events/weather.
    """
    out = add_time_features(df)

    if "dow" in out.columns:
        out["is_weekend"] = out["dow"].isin([5, 6]).astype(int)
    if "hour" in out.columns:
        out["is_rush_hour"] = out["hour"].isin([7, 8, 9, 16, 17, 18, 19]).astype(int)

    if "trip_distance" in out.columns:
        out["distance_bucket"] = _numeric_bin(
            out["trip_distance"],
            bins=[-np.inf, 1.0, 3.0, 8.0, np.inf],
        )

    if "event_count" in out.columns:
        out["event_level_num"] = _numeric_bin(
            out["event_count"],
            bins=[-0.1, 0.0, 50.0, 150.0, np.inf],
        )

    if "precip_in" in out.columns:
        out["precip_flag"] = (pd.to_numeric(out["precip_in"], errors="coerce") > 0).astype(int)

    temp_col = "temp_f" if "temp_f" in out.columns else "temp_c" if "temp_c" in out.columns else None
    if temp_col:
        out["temp_band_num"] = _numeric_bin(
            out[temp_col],
            bins=[-np.inf, 32.0, 50.0, 70.0, np.inf],
        )

    if "wind_m_s" in out.columns:
        out["wind_band_num"] = _numeric_bin(
            out["wind_m_s"],
            bins=[-np.inf, 3.0, 7.0, np.inf],
        )

    pickup_zone = out.get("PULocationID")
    dropoff_zone = out.get("DOLocationID")
    if pickup_zone is not None or dropoff_zone is not None:
        pickup_airport = (
            pd.to_numeric(pickup_zone, errors="coerce").isin(AIRPORT_LOCATION_IDS)
            if pickup_zone is not None
            else False
        )
        dropoff_airport = (
            pd.to_numeric(dropoff_zone, errors="coerce").isin(AIRPORT_LOCATION_IDS)
            if dropoff_zone is not None
            else False
        )
        out["is_airport_trip"] = (pickup_airport | dropoff_airport).astype(int)

    return out


def add_congestion_proxy(
    df: pd.DataFrame,
    duration_col: str = "trip_duration_sec",
    distance_col: str = "trip_distance",
    out_col: str = "avg_speed_mph",
) -> pd.DataFrame:
    """
    Approximate average trip speed (mph). Lower speed often indicates congestion.
    trip_distance in TLC is typically miles.
    """
    out = df.copy()
    if duration_col not in out.columns or distance_col not in out.columns:
        out[out_col] = np.nan
        return out
    dur_h = pd.to_numeric(out[duration_col], errors="coerce") / 3600.0
    dist = pd.to_numeric(out[distance_col], errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        speed = np.where(dur_h > 0, dist / dur_h, np.nan)
    out[out_col] = speed
    # Cap unrealistic values (GPS/dataset errors)
    out.loc[out[out_col] > 80, out_col] = np.nan
    return out


def bin_congestion_level(
    df: pd.DataFrame,
    speed_col: str = "avg_speed_mph",
    out_col: str = "congestion_level",
    quantiles: tuple = (0.33, 0.66),
) -> pd.DataFrame:
    """
    Ordinal congestion label: 0 = lighter traffic (higher speed), 2 = heavier.
    """
    out = df.copy()
    if speed_col not in out.columns:
        out = add_congestion_proxy(out)
    s = pd.to_numeric(out[speed_col], errors="coerce")
    valid = s.dropna()
    if len(valid) < 10:
        out[out_col] = 0
        return out
    q1, q2 = valid.quantile(quantiles[0]), valid.quantile(quantiles[1])
    out[out_col] = 0
    out.loc[s <= q1, out_col] = 2
    out.loc[(s > q1) & (s <= q2), out_col] = 1
    out.loc[s > q2, out_col] = 0
    return out


# Only explicitly approved weather measurements can enter the model.
# Never infer predictors from all numeric columns: TLC data contains post-trip
# fields (tips, fares, taxes) that would leak information at prediction time.
WEATHER_FEATURES = (
    "temp_f", "precip_in", "wind_m_s", "humidity", "relative_humidity",
    "pressure", "pressure_hpa", "cloud_cover", "visibility",
    "dew_point_f", "wind_speed_mph", "wind_dir_deg",
)


def pick_numeric_weather_features(df: pd.DataFrame, exclude: Optional[Iterable[str]] = None) -> List[str]:
    """Select only allowlisted, numeric pre-trip weather columns."""
    excluded = set(exclude or [])
    return [
        name for name in WEATHER_FEATURES
        if name in df.columns
        and name not in excluded
        and pd.api.types.is_numeric_dtype(df[name])
    ]


def filter_model_training_rows(
    df: pd.DataFrame,
    target_col: str,
    duration_col: str = "trip_duration_sec",
    distance_col: str = "trip_distance",
) -> pd.DataFrame:
    """
    Remove obvious data errors before training.

    This keeps the model focused on normal taxi trips instead of impossible
    records such as zero-mile rides, extreme durations, or unknown TLC zones.
    """
    out = df.copy()

    if duration_col in out.columns:
        duration = pd.to_numeric(out[duration_col], errors="coerce")
        out = out[(duration >= 60) & (duration <= 4 * 3600)]

    if distance_col in out.columns:
        distance = pd.to_numeric(out[distance_col], errors="coerce")
        out = out[(distance >= 0.1) & (distance <= 100)]

    if "avg_speed_mph" in out.columns:
        speed = pd.to_numeric(out["avg_speed_mph"], errors="coerce")
        out = out[speed.isna() | ((speed >= 1) & (speed <= 80))]

    for col in ["PULocationID", "DOLocationID"]:
        if col in out.columns:
            zone = pd.to_numeric(out[col], errors="coerce")
            out = out[~zone.isin(UNKNOWN_LOCATION_IDS)]

    if target_col in out.columns:
        out = out.dropna(subset=[target_col])

    return out


def build_model_matrix(
    df: pd.DataFrame,
    target_col: str,
    extra_features: Optional[List[str]] = None,
    exclude_features: Optional[List[str]] = None,
) -> tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Build X, y and feature name list. Drops rows with missing target.
    """
    extra_features = extra_features or []
    if df.columns.duplicated().any():
        dup = df.columns[df.columns.duplicated()].tolist()
        logger.warning("Duplicate column names from Spark merge; keeping first: %s", dup)
        df = df.loc[:, ~df.columns.duplicated()].copy()
    df = add_domain_features(df)
    df = add_congestion_proxy(df)
    df = filter_model_training_rows(df, target_col=target_col)
    weather_feats = pick_numeric_weather_features(df)
    base = [
        "hour",
        "dow",
        "month",
        "is_weekend",
        "is_rush_hour",
        "trip_distance",
        "distance_bucket",
        "event_count",
        "event_level_num",
        "is_airport_trip",
        "precip_flag",
        "temp_band_num",
        "wind_band_num",
    ]
    base = [c for c in base if c in df.columns]
    excl = set(exclude_features or [])
    feat_names = base + weather_feats + extra_features
    feat_names = [
        c
        for c in feat_names
        if c in df.columns and c != target_col and c not in excl
    ]
    feat_names = list(dict.fromkeys(feat_names))

    d = df.dropna(subset=[target_col]).copy()
    # Preserve missing values; training-only imputation happens after splitting.
    X = d[feat_names]
    y = d[target_col]
    logger.info("Model matrix: %s samples, %s features", len(X), len(feat_names))
    return X, y, feat_names
