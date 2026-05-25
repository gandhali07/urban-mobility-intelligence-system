"""
DBSCAN clustering on pickup locations to discover spatial congestion hotspots.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

logger = logging.getLogger(__name__)

EARTH_RADIUS_M = 6_371_000.0


def _lat_lon_to_xy_meters(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Equirectangular projection around mean latitude (good enough for city-scale DBSCAN)."""
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    lat0 = float(np.mean(lat_rad))
    x = (lon_rad - np.mean(lon_rad)) * np.cos(lat0) * EARTH_RADIUS_M
    y = (lat_rad - np.mean(lat_rad)) * EARTH_RADIUS_M
    return np.column_stack([x, y])


def run_dbscan_hotspots(
    df: pd.DataFrame,
    lat_col: str = "pickup_lat",
    lon_col: str = "pickup_lon",
    eps_miles: float = 0.3,
    min_samples: int = 15,
    sample_size: Optional[int] = 5000,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run DBSCAN on pickup (lat, lon). eps_miles is neighborhood radius in miles.

    Returns:
        points: rows aligned with df with column hotspot_cluster (-1 = noise)
        centers: mean lat/lon per cluster and point counts
    """
    out = df.copy()
    out["hotspot_cluster"] = -1

    if lat_col not in df.columns or lon_col not in df.columns:
        logger.warning(
            "%s/%s not found - skipping DBSCAN hotspot clustering.",
            lat_col,
            lon_col,
        )
        return out, pd.DataFrame()

    use_idx = df[[lat_col, lon_col]].dropna().index
    if len(use_idx) == 0:
        logger.warning("No coordinates for DBSCAN.")
        return out, pd.DataFrame()

    use = df.loc[use_idx, [lat_col, lon_col]].astype(float)
    if sample_size is not None and len(use) > sample_size:
        use = use.sample(sample_size, random_state=random_state)
        logger.info("DBSCAN sample size: %s (of %s coordinate rows)", sample_size, len(use_idx))

    lat = use[lat_col].values
    lon = use[lon_col].values
    X = _lat_lon_to_xy_meters(lat, lon)
    eps_m = eps_miles * 1609.34
    db = DBSCAN(eps=eps_m, min_samples=min_samples, metric="euclidean")
    labels = db.fit_predict(X)
    out.loc[use.index, "hotspot_cluster"] = labels

    noise = int((labels == -1).sum())
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    logger.info("DBSCAN: %s clusters, %s noise points (sample)", n_clusters, noise)

    labeled = out.loc[use.index].copy()
    labeled["hotspot_cluster"] = labels
    centers = (
        labeled[labeled["hotspot_cluster"] >= 0]
        .groupby("hotspot_cluster")
        .agg(
            center_lat=(lat_col, "mean"),
            center_lon=(lon_col, "mean"),
            n_points=(lat_col, "count"),
        )
        .reset_index()
    )
    return out, centers
