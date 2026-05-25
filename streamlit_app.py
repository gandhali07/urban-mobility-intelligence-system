"""
Streamlit dashboard for the Urban Mobility Intelligence project.

Run:
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src import config
from src.map_visualization import build_demo_map


ANALYTICS_DIR = config.OUTPUTS_DIR / "analytics"


def list_map_files() -> list[Path]:
    config.ensure_output_dirs()
    return sorted(config.MAPS_DIR.glob("*.html"), key=lambda p: p.name.lower())


def default_map_choice(files: list[Path]) -> int:
    preferred = ["urban_mobility_map.html", "urban_mobility_demo.html"]
    names = [p.name for p in files]
    for target in preferred:
        if target in names:
            return names.index(target)
    return 0


def hide_legacy_title_banner(map_html: str) -> str:
    """
    Remove older in-map title banners from previously generated HTML files.
    New files will not include this banner.
    """
    cleanup_script = """
    <script>
    (function () {
      const target = "Urban Mobility Intelligence - NYC";
      const nodes = Array.from(document.querySelectorAll("div"));
      for (const el of nodes) {
        if ((el.textContent || "").trim() === target) {
          el.remove();
        }
      }
    })();
    </script>
    """
    return map_html + cleanup_script


@st.cache_data
def read_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


@st.cache_data
def read_model_meta(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def show_table(path: Path, columns: list[str] | None = None, n: int = 25) -> pd.DataFrame:
    df = read_csv(str(path))
    if df.empty:
        st.warning(f"Missing or empty file: `{path}`")
        return df
    view = df[columns] if columns else df
    st.dataframe(view.head(n), use_container_width=True, hide_index=True)
    return df


def metric_row(items: list[tuple[str, str | float | int]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


st.set_page_config(
    page_title="Urban Mobility Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    div.block-container {
      padding-top: 0.6rem;
      padding-bottom: 0.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Urban Mobility Intelligence System")
st.caption("NYC taxi trips aligned with February 2023 weather, events, model explainability, and map outputs.")

tabs = st.tabs(
    [
        "Map",
        "Event Impact",
        "Weather Impact",
        "Time Analysis",
        "Zone Analysis",
        "Airport Trips",
        "Model + SHAP",
        "Prediction Demo",
    ]
)

with tabs[0]:
    st.subheader("Interactive Mobility Map")
    map_files = list_map_files()

    if not map_files:
        st.warning("No map HTML files found in `outputs/maps`.")
        st.code("python main.py --step demo_map", language="bash")
    else:
        action_col, map_col = st.columns([1, 3])

        with action_col:
            st.write("### Map Actions")
            st.write("Use the layer control inside the map to toggle heatmap, hotspots, and events.")
            if st.button("Generate Demo Map", use_container_width=True):
                out_path = config.MAPS_DIR / "urban_mobility_demo.html"
                build_demo_map(out_path=out_path)
                st.success("Demo map generated.")
                st.rerun()

        with map_col:
            selected_index = default_map_choice(map_files)
            selected_map = st.selectbox(
                "Select map file",
                options=map_files,
                index=selected_index,
                format_func=lambda p: p.name,
            )

        map_html = selected_map.read_text(encoding="utf-8")
        map_html = hide_legacy_title_banner(map_html)
        components.html(map_html, height=840, scrolling=False)

with tabs[1]:
    st.subheader("Event Impact")
    st.write("Compares trips by daily event intensity after aligning event dates to February 2023 taxi trips.")
    df = show_table(
        ANALYTICS_DIR / "event_impact.csv",
        [
            "event_level",
            "trips",
            "avg_duration_min",
            "median_duration_min",
            "avg_distance_miles",
            "avg_speed_mph",
            "avg_event_count",
        ],
    )
    if not df.empty:
        st.bar_chart(df.set_index("event_level")["avg_duration_min"])

with tabs[2]:
    st.subheader("Weather Impact")
    st.write("Shows how temperature, wind, and humidity bands relate to duration and speed.")
    df = show_table(ANALYTICS_DIR / "weather_impact.csv")
    if not df.empty:
        selected = st.selectbox(
            "Weather dimension",
            sorted(df["weather_dimension"].dropna().unique()),
        )
        part = df[df["weather_dimension"] == selected]
        st.bar_chart(part.set_index("weather_band")["avg_duration_min"])

with tabs[3]:
    st.subheader("Time Analysis")
    st.write("Summarizes trip behavior by hour, day of week, weekend flag, and rush-hour flag.")
    df = show_table(ANALYTICS_DIR / "time_mobility.csv")
    if not df.empty:
        selected = st.selectbox(
            "Time dimension",
            sorted(df["time_dimension"].dropna().unique()),
        )
        part = df[df["time_dimension"] == selected].copy()
        st.bar_chart(part.set_index("time_value")["avg_duration_min"])

with tabs[4]:
    st.subheader("Zone Pair Analysis")
    st.write("Ranks pickup/dropoff taxi-zone pairs using official TLC zone names.")
    df = show_table(
        ANALYTICS_DIR / "zone_pair.csv",
        [
            "zone_pair_name",
            "borough_pair",
            "trips",
            "avg_duration_min",
            "median_duration_min",
            "avg_distance_miles",
            "avg_speed_mph",
        ],
        n=30,
    )
    if not df.empty:
        top = df.head(12).set_index("zone_pair_name")
        st.bar_chart(top["trips"])

with tabs[5]:
    st.subheader("Airport Trips")
    st.write("Compares trips involving airport taxi zones against all other trips.")
    df = show_table(ANALYTICS_DIR / "airport_trip.csv")
    if not df.empty:
        label_map = {0: "Non-airport", 1: "Airport"}
        df["trip_type"] = df["is_airport_trip"].map(label_map)
        metric_row(
            [
                ("Airport avg duration", f"{df.loc[df['is_airport_trip'] == 1, 'avg_duration_min'].iloc[0]:.1f} min"),
                ("Non-airport avg duration", f"{df.loc[df['is_airport_trip'] == 0, 'avg_duration_min'].iloc[0]:.1f} min"),
                ("Airport avg distance", f"{df.loc[df['is_airport_trip'] == 1, 'avg_distance_miles'].iloc[0]:.1f} mi"),
            ]
        )
        st.bar_chart(df.set_index("trip_type")[["avg_duration_min", "avg_distance_miles"]])

with tabs[6]:
    st.subheader("Model Results and SHAP Explainability")
    meta = read_model_meta(str(config.MODELS_DIR / "xgboost_model_meta.json"))
    if not meta:
        st.warning("Model metadata not found. Run `python main.py` first.")
    else:
        metrics = meta.get("metrics", {})
        metric_row(
            [
                ("Task", metrics.get("task", "n/a")),
                ("MAE", f"{float(metrics.get('mae', 0)):.1f} sec" if "mae" in metrics else "n/a"),
                ("R2", f"{float(metrics.get('r2', 0)):.3f}" if "r2" in metrics else "n/a"),
                ("Features", len(meta.get("feature_names", []))),
            ]
        )
        with st.expander("Feature names"):
            st.write(", ".join(meta.get("feature_names", [])))

    img_col1, img_col2 = st.columns(2)
    bar_path = config.FIGURES_DIR / "shap_summary_bar.png"
    bee_path = config.FIGURES_DIR / "shap_summary_beeswarm.png"
    with img_col1:
        if bar_path.exists():
            st.image(str(bar_path), caption="SHAP global feature importance")
    with img_col2:
        if bee_path.exists():
            st.image(str(bee_path), caption="SHAP feature impact by trip")

with tabs[7]:
    st.subheader("Prediction Demo")
    st.write("Use the trained model from the command line to estimate trip duration from two locations.")
    st.code(
        'python predict_trip.py --pickup "Times Square" --dropoff "JFK Airport" --datetime "2023-02-10 17:30"',
        language="powershell",
    )
    st.write("The prediction interface returns estimated duration, estimated congestion, approximate distance, and event count.")
