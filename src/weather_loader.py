"""
Load Kaggle-style multi-city weather CSVs (one file per variable, wide format).
We extract a single city column (default: "New York") and merge on datetime.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from src import config

logger = logging.getLogger(__name__)

# Default stem -> output column (numeric features for the model)
DEFAULT_WEATHER_FILES: dict[str, str] = {
    "temperature": "temp_k",
    "humidity": "humidity",
    "pressure": "pressure",
    "wind_speed": "wind_m_s",
    "wind_direction": "wind_dir_deg",
}


def load_nyc_weather_from_kaggle_folder(
    weather_dir: Path | str | None = None,
    city: str = "New York",
    file_map: Optional[dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Build an hourly long-format DataFrame for one city from wide CSVs.

    Expected files under e.g. data/raw/nyc_weather/:
    temperature.csv, humidity.csv, pressure.csv, wind_speed.csv, wind_direction.csv
    Each has columns: datetime, <city1>, <city2>, ...
    """
    d = Path(weather_dir) if weather_dir is not None else (config.RAW_DATA_DIR / "nyc_weather")
    if not d.is_dir():
        return pd.DataFrame()

    fmap = file_map or DEFAULT_WEATHER_FILES
    base: Optional[pd.DataFrame] = None
    for stem, out_col in fmap.items():
        fp = d / f"{stem}.csv"
        if not fp.exists():
            logger.warning("Weather file missing, skipping: %s", fp)
            continue
        part = pd.read_csv(fp, low_memory=False)
        part.columns = [c.strip() for c in part.columns]
        if "datetime" not in part.columns:
            raise ValueError(f"{fp} must have a 'datetime' column")
        ccol = _resolve_city_column(part.columns, city)
        if ccol is None:
            raise ValueError(f"City {city!r} not found in {fp.name}; columns: {list(part.columns)[:8]}...")

        sub = part[["datetime", ccol]].copy()
        sub = sub.rename(columns={ccol: out_col, "datetime": "time"})
        if base is None:
            base = sub
        else:
            base = base.merge(sub, on="time", how="outer")

    if base is None or base.empty:
        return pd.DataFrame()

    base["time"] = pd.to_datetime(base["time"], errors="coerce")
    base = base.dropna(subset=["time"])
    # Derived feature for human-readable maps / interpretability
    if "temp_k" in base.columns:
        base["temp_f"] = (pd.to_numeric(base["temp_k"], errors="coerce") - 273.15) * 9.0 / 5.0 + 32.0

    base = base.sort_values("time").reset_index(drop=True)
    logger.info("Built NYC weather from folder %s: %s rows, cols=%s", d, len(base), list(base.columns))
    return base


def _resolve_city_column(columns: list[str], city: str) -> Optional[str]:
    wanted = city.strip()
    for c in columns:
        if c == wanted or c.strip() == wanted:
            return c
    low = {c.lower().strip(): c for c in columns}
    if wanted.lower() in low:
        return low[wanted.lower()]
    if "new york" in low and "new york" in wanted.lower():
        return low["new york"]
    return None
