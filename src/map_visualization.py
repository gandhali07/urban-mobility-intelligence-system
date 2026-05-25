"""
Folium interactive map: congestion hotspots, heatmap, events, demo layers.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import folium
import numpy as np
import pandas as pd
from folium.plugins import Fullscreen, HeatMap, MiniMap

from src import config

logger = logging.getLogger(__name__)

NYC_CENTER = (40.7580, -73.9855)
COLOR_SEVERITY = {0: "#2ecc71", 1: "#f1c40f", 2: "#e74c3c"}


def _add_map_legend(m: folium.Map) -> None:
    """Inject a simple HTML legend for congestion severity."""
    legend_html = """
    <div style="
        position: fixed;
        bottom: 28px;
        left: 28px;
        z-index: 9999;
        background: rgba(255,255,255,0.95);
        border: 2px solid #444;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 13px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    ">
      <div style="font-weight: 700; margin-bottom: 6px;">Congestion Severity</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#2ecc71;border-radius:50%;margin-right:6px;"></span>Low</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#f1c40f;border-radius:50%;margin-right:6px;"></span>Medium</div>
      <div><span style="display:inline-block;width:10px;height:10px;background:#e74c3c;border-radius:50%;margin-right:6px;"></span>High</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))


def build_urban_mobility_map(
    hotspots_df: pd.DataFrame,
    heatmap_points: pd.DataFrame,
    events_df: Optional[pd.DataFrame] = None,
    out_path: Path | None = None,
    severity_col: str = "congestion_level",
) -> folium.Map:
    """
    Create a presentation-friendly map:
    - HeatMap layer from heatmap_points (lat, lon, optional weight)
    - Circle markers for DBSCAN hotspot centers with popups
    - Event markers if provided (lat, lon, name, event_date)
    """
    out_path = out_path or (config.MAPS_DIR / "urban_mobility_map.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    m = folium.Map(location=NYC_CENTER, zoom_start=12, tiles=None)
    folium.TileLayer("OpenStreetMap", name="Street").add_to(m)
    folium.TileLayer("CartoDB dark_matter", name="Dark").add_to(m)
    Fullscreen(position="topright", title="Full screen").add_to(m)
    MiniMap(toggle_display=True).add_to(m)

    # --- Heatmap data ---
    hm_cols = [c for c in ("lat", "pickup_lat") if c in heatmap_points.columns]
    lat_c = hm_cols[0] if hm_cols else None
    lon_c = "lon" if "lon" in heatmap_points.columns else (
        "pickup_lon" if "pickup_lon" in heatmap_points.columns else None
    )
    weight_c = "weight" if "weight" in heatmap_points.columns else None

    if lat_c and lon_c:
        sub = heatmap_points[[lat_c, lon_c] + ([weight_c] if weight_c else [])].dropna()
        heat_data: List[List[Any]] = []
        for _, row in sub.iterrows():
            if weight_c:
                heat_data.append([float(row[lat_c]), float(row[lon_c]), float(row[weight_c])])
            else:
                heat_data.append([float(row[lat_c]), float(row[lon_c]), 0.5])
        if heat_data:
            fg_heat = folium.FeatureGroup(name="Traffic density heatmap", show=True)
            HeatMap(
                heat_data,
                radius=16,
                blur=20,
                min_opacity=0.35,
                gradient={
                    0.2: "#1f77b4",
                    0.45: "#2ecc71",
                    0.65: "#f1c40f",
                    0.85: "#ff7f0e",
                    1.0: "#e74c3c",
                },
            ).add_to(fg_heat)
            fg_heat.add_to(m)

    # --- Hotspot markers (filter-friendly FeatureGroup) ---
    fg_hot = folium.FeatureGroup(name="Hotspots (all)", show=True)
    fg_low = folium.FeatureGroup(name="Hotspots - Low", show=False)
    fg_med = folium.FeatureGroup(name="Hotspots - Medium", show=False)
    fg_high = folium.FeatureGroup(name="Hotspots - High", show=True)
    for _, row in hotspots_df.iterrows():
        lat = float(row.get("center_lat", row.get("lat", 0)))
        lon = float(row.get("center_lon", row.get("lon", 0)))
        sev = int(row.get(severity_col, 1)) if severity_col in row.index else 1
        color = COLOR_SEVERITY.get(sev, "#3498db")
        popup_html = (
            f"<b>Zone</b> {row.get('hotspot_cluster', row.get('zone_id', '?'))}<br/>"
            f"<b>Trips / weight</b> {row.get('n_points', row.get('weight', 'n/a'))}<br/>"
            f"<b>Severity</b> {sev}"
        )
        radius = 8 + min(int(row.get("n_points", 10)) // 50, 20)
        tooltip = f"Hotspot {row.get('hotspot_cluster', row.get('zone_id', '?'))} | Severity {sev}"

        def _mk_marker() -> folium.CircleMarker:
            return folium.CircleMarker(
                location=(lat, lon),
                radius=radius,
                color="#ffffff",
                weight=1.5,
                fill=True,
                fill_color=color,
                fill_opacity=0.82,
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=tooltip,
            )

        _mk_marker().add_to(fg_hot)
        if sev <= 0:
            _mk_marker().add_to(fg_low)
        elif sev == 1:
            _mk_marker().add_to(fg_med)
        else:
            _mk_marker().add_to(fg_high)
    fg_hot.add_to(m)
    fg_low.add_to(m)
    fg_med.add_to(m)
    fg_high.add_to(m)

    # --- Events ---
    if events_df is not None and not events_df.empty:
        fg_ev = folium.FeatureGroup(name="Events", show=True)
        lat_e = "lat" if "lat" in events_df.columns else None
        lon_e = "lon" if "lon" in events_df.columns else None
        if lat_e and lon_e:
            for _, er in events_df.dropna(subset=[lat_e, lon_e]).iterrows():
                name = er.get("name", er.get("event_name", "Event"))
                when = er.get("event_date", "")
                folium.CircleMarker(
                    location=(float(er[lat_e]), float(er[lon_e])),
                    radius=3,
                    color="#9b59b6",
                    fill=True,
                    fill_color="#9b59b6",
                    fill_opacity=0.6,
                    weight=1,
                    popup=folium.Popup(
                        f"<b>{name}</b><br/><b>Date:</b> {when}<br/><b>Type:</b> {er.get('category', 'general')}",
                        max_width=260,
                    ),
                    tooltip=name,
                ).add_to(fg_ev)
        fg_ev.add_to(m)

    _add_map_legend(m)
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(str(out_path))
    logger.info("Saved interactive map to %s", out_path)
    return m


def sample_demo_data() -> Dict[str, pd.DataFrame]:
    """
    Synthetic NYC-ish points for first-run demo (no external files required).
    """
    rng = pd.Series(range(120))
    r1, r2, r3 = np.random.default_rng(1), np.random.default_rng(2), np.random.default_rng(3)
    heatmap_points = pd.DataFrame(
        {
            "pickup_lat": 40.75 + rng * 0.001 + r1.normal(0, 0.01, len(rng)),
            "pickup_lon": -73.99 + rng * 0.0008 + r2.normal(0, 0.01, len(rng)),
            "weight": r3.integers(1, 8, len(rng)),
        }
    )
    hotspots_df = pd.DataFrame(
        {
            "hotspot_cluster": [0, 1, 2, 3],
            "center_lat": [40.7589, 40.7484, 40.7614, 40.7282],
            "center_lon": [-73.9851, -73.9857, -73.9776, -73.9942],
            "n_points": [400, 320, 280, 210],
            "congestion_level": [2, 1, 2, 0],
        }
    )
    events_df = pd.DataFrame(
        {
            "name": ["Madison Square Garden Event", "Javits Convention", "Central Park Run"],
            "event_date": pd.to_datetime(["2024-06-01", "2024-06-02", "2024-06-03"]),
            "lat": [40.7505, 40.7580, 40.7851],
            "lon": [-73.9934, -73.9965, -73.9683],
        }
    )
    return {
        "heatmap_points": heatmap_points,
        "hotspots_df": hotspots_df,
        "events_df": events_df,
    }


def build_demo_map(out_path: Path | None = None) -> folium.Map:
    """Generate the first-version map from built-in sample data."""
    data = sample_demo_data()
    return build_urban_mobility_map(
        hotspots_df=data["hotspots_df"],
        heatmap_points=data["heatmap_points"],
        events_df=data["events_df"],
        out_path=out_path or (config.MAPS_DIR / "urban_mobility_demo.html"),
    )
