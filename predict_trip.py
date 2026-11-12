"""
Small prediction interface for the Urban Mobility Intelligence project.

Examples:
    python predict_trip.py --pickup "Times Square" --dropoff "JFK Airport" --datetime "2023-02-10 17:30"
    python predict_trip.py --pickup-lat 40.7580 --pickup-lon -73.9855 --dropoff-lat 40.6413 --dropoff-lon -73.7781 --datetime "2023-02-10 17:30"
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from src import config
from src.data_loading import load_events_pandas, load_weather_pandas
from src.preprocessing import preprocess_events_df, preprocess_weather_df
from src.feature_engineering import AIRPORT_LOCATION_IDS, add_domain_features

logging.getLogger().setLevel(logging.ERROR)

KNOWN_LOCATIONS: dict[str, dict[str, float | int]] = {
    "times square": {"lat": 40.7580, "lon": -73.9855, "location_id": 230},
    "grand central": {"lat": 40.7527, "lon": -73.9772, "location_id": 161},
    "penn station": {"lat": 40.7506, "lon": -73.9935, "location_id": 186},
    "central park": {"lat": 40.7812, "lon": -73.9665, "location_id": 43},
    "wall street": {"lat": 40.7060, "lon": -74.0086, "location_id": 231},
    "jfk airport": {"lat": 40.6413, "lon": -73.7781, "location_id": 132},
    "laguardia airport": {"lat": 40.7769, "lon": -73.8740, "location_id": 138},
    "newark airport": {"lat": 40.6895, "lon": -74.1745, "location_id": 1},
}


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance in miles."""
    radius_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    )
    return 2 * radius_miles * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def resolve_location(name: str | None, lat: float | None, lon: float | None) -> dict[str, float | int | None]:
    """Resolve either a known place name or explicit coordinates."""
    if name:
        key = name.strip().lower()
        if key not in KNOWN_LOCATIONS:
            known = ", ".join(sorted(KNOWN_LOCATIONS))
            raise ValueError(f"Unknown location {name!r}. Known names: {known}")
        loc = KNOWN_LOCATIONS[key].copy()
        loc["name"] = name
        return loc
    if lat is None or lon is None:
        raise ValueError("Provide either a location name or both latitude and longitude.")
    return {"name": "custom point", "lat": lat, "lon": lon, "location_id": None}


def load_feature_names(meta_path: Path) -> list[str]:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return list(meta["feature_names"])


def build_defaults(feature_names: list[str], sample_rows: int = 100_000) -> dict[str, float]:
    """
    Build numeric defaults from raw taxi data.
    Unknown features are set to zero later.
    """
    taxi_path = config.resolve_taxi_path()
    if not taxi_path.exists():
        taxi_path = config.RAW_DATA_DIR / "yellow_taxi_data.parquet"

    defaults: dict[str, float] = {}
    if taxi_path.exists():
        if taxi_path.suffix.lower() in (".parquet", ".parq"):
            taxi = pd.read_parquet(taxi_path)
            if len(taxi) > sample_rows:
                taxi = taxi.sample(sample_rows, random_state=config.RANDOM_STATE)
        else:
            taxi = pd.read_csv(taxi_path, nrows=sample_rows, low_memory=False)

        for col in feature_names:
            if col in taxi.columns and pd.api.types.is_numeric_dtype(taxi[col]):
                val = pd.to_numeric(taxi[col], errors="coerce").median()
                defaults[col] = float(val) if pd.notna(val) else 0.0

    for col in feature_names:
        defaults.setdefault(col, 0.0)
    return defaults


def weather_values_for_time(trip_dt: datetime) -> dict[str, float]:
    weather = preprocess_weather_df(load_weather_pandas())
    if weather.empty or "time" not in weather.columns:
        return {}

    out = weather.copy()
    out["time"] = pd.to_datetime(out["time"], errors="coerce")
    out = out.dropna(subset=["time"]).sort_values("time")
    if out.empty:
        return {}

    # Only use observations available by the requested pickup time.
    available = out.loc[out["time"] <= pd.Timestamp(trip_dt)]
    if available.empty:
        return {}
    row = available.iloc[-1]
    values: dict[str, float] = {}
    for col in ["temp_f", "temp_c", "precip_in", "humidity", "pressure", "wind_m_s", "wind_dir_deg"]:
        if col in row.index and pd.notna(row[col]):
            values[col] = float(row[col])
    return values


def count_events_on_date(events: pd.DataFrame, trip_dt: datetime) -> int:
    """Count events by the same calendar-day convention as the Spark training join.

    Missing or unparseable date schemas are errors, not evidence of zero events.
    """
    if events.empty:
        return 0
    date_col = next(
        (name for name in ("event_date", "Start Date/Time", "start_date_time", "date")
         if name in events.columns),
        None,
    )
    if date_col is None:
        raise ValueError("Event data has no recognized date column.")
    dates = pd.to_datetime(events[date_col], errors="coerce")
    if dates.notna().sum() == 0:
        raise ValueError(f"Event date column {date_col!r} contains no parseable dates.")
    return int((dates.dt.date == trip_dt.date()).sum())


def event_count_for_date(trip_dt: datetime) -> int:
    return count_events_on_date(load_events_pandas(), trip_dt)


def build_prediction_row(args: argparse.Namespace, feature_names: list[str], imputation_values: dict[str, float] | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    pickup = resolve_location(args.pickup, args.pickup_lat, args.pickup_lon)
    dropoff = resolve_location(args.dropoff, args.dropoff_lat, args.dropoff_lon)
    trip_dt = pd.to_datetime(args.datetime).to_pydatetime()

    straight_miles = haversine_miles(
        float(pickup["lat"]),
        float(pickup["lon"]),
        float(dropoff["lat"]),
        float(dropoff["lon"]),
    )
    trip_distance = args.trip_distance if args.trip_distance is not None else straight_miles * 1.35

    row: dict[str, float] = {}
    row.update(
        {
            "hour": float(trip_dt.hour),
            "dow": float(trip_dt.weekday()),
            "month": float(trip_dt.month),
            "trip_distance": float(trip_distance),
            "event_count": float(event_count_for_date(trip_dt)),
        }
    )

    if pickup.get("location_id") is not None:
        row["PULocationID"] = float(pickup["location_id"])
    if dropoff.get("location_id") is not None:
        row["DOLocationID"] = float(dropoff["location_id"])

    row.update(weather_values_for_time(trip_dt))

    # Reuse the exact feature engineering function used during training.
    # Missing model features are filled using training medians from metadata.
    raw = pd.DataFrame([{
        **row,
        "pickup_ts": pd.Timestamp(trip_dt),
        "PULocationID": pickup.get("location_id"),
        "DOLocationID": dropoff.get("location_id"),
    }])
    engineered = add_domain_features(raw)
    X = engineered.reindex(columns=feature_names).apply(
        pd.to_numeric, errors="coerce"
    ).astype(float)
    if imputation_values is not None:
        X = X.fillna(pd.Series(imputation_values)).fillna(0.0)
    else:
        raise ValueError("Model metadata lacks training imputation values; retrain with main.py.")
    details = {
        "pickup": pickup,
        "dropoff": dropoff,
        "datetime": trip_dt,
        "straight_miles": straight_miles,
        "model_trip_distance": trip_distance,
        "event_count": int(row.get("event_count", 0)),
    }
    return X, details


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict NYC taxi trip duration from two locations.")
    parser.add_argument("--pickup", help="Known pickup name, e.g. 'Times Square'")
    parser.add_argument("--dropoff", help="Known dropoff name, e.g. 'JFK Airport'")
    parser.add_argument("--pickup-lat", type=float)
    parser.add_argument("--pickup-lon", type=float)
    parser.add_argument("--dropoff-lat", type=float)
    parser.add_argument("--dropoff-lon", type=float)
    parser.add_argument("--datetime", default=datetime.now().strftime("%Y-%m-%d %H:%M"))
    parser.add_argument("--trip-distance", type=float, help="Optional road distance in miles.")
    args = parser.parse_args()

    model_path = config.MODELS_DIR / "xgboost_model.json"
    meta_path = config.MODELS_DIR / "xgboost_model_meta.json"
    if not model_path.exists() or not meta_path.exists():
        raise FileNotFoundError("Model files missing. Run main.py first.")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("metrics", {}).get("task") != "regression":
        raise ValueError("The prediction CLI requires a trip-duration regression model.")
    feature_names = list(meta["feature_names"])
    X, details = build_prediction_row(args, feature_names, meta.get("imputation_values"))

    model = XGBRegressor()
    model.load_model(str(model_path))
    pred_sec = max(0.0, float(model.predict(X)[0]))
    pred_min = pred_sec / 60.0

    speed_mph = details["model_trip_distance"] / max(pred_sec / 3600.0, 1e-9)
    if speed_mph < 8:
        congestion = "High"
    elif speed_mph < 16:
        congestion = "Medium"
    else:
        congestion = "Low"

    print("\nUrban Mobility Prediction")
    print("-------------------------")
    print(f"Pickup:  {details['pickup']['name']} ({details['pickup']['lat']}, {details['pickup']['lon']})")
    print(f"Dropoff: {details['dropoff']['name']} ({details['dropoff']['lat']}, {details['dropoff']['lon']})")
    print(f"Date/time: {details['datetime']:%Y-%m-%d %H:%M}")
    print(f"Approx distance used: {details['model_trip_distance']:.2f} miles")
    print(f"Events on that date: {details['event_count']}")
    print(f"Estimated duration: {pred_min:.1f} minutes")
    print(f"Estimated congestion: {congestion}")
    print("\nNote: this uses the cleaned pre-trip model, so payment-after-trip fields like total_amount and tip_amount are not required.")


if __name__ == "__main__":
    main()
