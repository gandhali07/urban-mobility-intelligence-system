"""
Detailed analytics helpers for the Urban Mobility Intelligence project.

This module creates explainable summary tables from the current three datasets:
taxi trips, weather, and NYC events. It is intentionally separate from the main
training pipeline so we can expand analysis without disturbing model execution.

Run from project root:
    python -m src.analytics --max-rows 100000
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from src import config
from src.data_loading import load_events_pandas, load_weather_pandas
from src.feature_engineering import add_congestion_proxy, add_time_features
from src.preprocessing import (
    DEFAULT_TAXI_COLUMN_ALIASES,
    preprocess_events_df,
    preprocess_weather_df,
)

logger = logging.getLogger(__name__)


AFTER_TRIP_COLUMNS = {
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "Airport_fee",
    "payment_type",
}

AIRPORT_LOCATION_IDS = {1, 132, 138}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _sentence_number(value: float, unit: str = "") -> str:
    suffix = f" {unit}" if unit else ""
    return f"{value:,.1f}{suffix}"


def load_taxi_zone_lookup(path: Path | str | None = None) -> pd.DataFrame:
    """Load official TLC taxi zone labels if available."""
    lookup_path = Path(path) if path else config.RAW_DATA_DIR / "taxi_zone_lookup.csv"
    if not lookup_path.exists():
        logger.warning("Taxi zone lookup missing at %s", lookup_path)
        return pd.DataFrame()
    zones = pd.read_csv(lookup_path)
    zones = zones.rename(
        columns={
            "LocationID": "location_id",
            "Borough": "borough",
            "Zone": "zone",
            "service_zone": "service_zone",
        }
    )
    zones["location_id"] = pd.to_numeric(zones["location_id"], errors="coerce").astype("Int64")
    return zones


def load_taxi_for_analytics(
    path: Path | str | None = None,
    max_rows: int | None = 100_000,
) -> pd.DataFrame:
    """Load taxi data with pandas for analysis tables."""
    taxi_path = Path(path) if path else config.resolve_taxi_path()
    if not taxi_path.exists():
        raise FileNotFoundError(f"Taxi data not found at {taxi_path}")

    logger.info("Loading taxi analytics data from %s", taxi_path)
    if taxi_path.suffix.lower() in (".parquet", ".parq"):
        df = pd.read_parquet(taxi_path)
        if max_rows and len(df) > max_rows:
            df = df.sample(max_rows, random_state=config.RANDOM_STATE)
    else:
        df = pd.read_csv(taxi_path, nrows=max_rows, low_memory=False)
    logger.info("Taxi analytics shape: %s", df.shape)
    return df


def preprocess_taxi_for_analytics(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize taxi fields and create trip duration in seconds."""
    out = df.copy()
    for old, new in DEFAULT_TAXI_COLUMN_ALIASES.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old: new})

    if "pickup_ts" in out.columns:
        out["pickup_ts"] = pd.to_datetime(out["pickup_ts"], errors="coerce")
    if "dropoff_ts" in out.columns:
        out["dropoff_ts"] = pd.to_datetime(out["dropoff_ts"], errors="coerce")

    if {"pickup_ts", "dropoff_ts"}.issubset(out.columns):
        out["trip_duration_sec"] = (
            out["dropoff_ts"] - out["pickup_ts"]
        ).dt.total_seconds()
        out = out[out["trip_duration_sec"].between(1, 24 * 3600)]

    if "trip_distance" in out.columns:
        out["trip_distance"] = pd.to_numeric(out["trip_distance"], errors="coerce")
        out = out[out["trip_distance"].fillna(0) > 0]

    logger.info("Taxi analytics after preprocessing: %s", out.shape)
    return out


def merge_context_for_analytics(
    taxi: pd.DataFrame,
    weather: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    """Attach hourly weather and daily event counts to taxi trips."""
    out = taxi.copy()

    if "pickup_ts" not in out.columns:
        return out

    if not weather.empty and "time" in weather.columns:
        w = weather.copy()
        w["_pickup_hour"] = pd.to_datetime(w["time"], errors="coerce").dt.floor("h")
        out["_pickup_hour"] = pd.to_datetime(out["pickup_ts"], errors="coerce").dt.floor("h")
        out = out.merge(
            w.drop(columns=["time"], errors="ignore"),
            on="_pickup_hour",
            how="left",
        ).drop(columns=["_pickup_hour"], errors="ignore")

    if not events.empty and "event_date" in events.columns:
        event_days = pd.to_datetime(events["event_date"], errors="coerce").dt.date
        daily_events = (
            event_days.dropna()
            .value_counts()
            .rename_axis("trip_date")
            .reset_index(name="event_count")
        )
        out["trip_date"] = pd.to_datetime(out["pickup_ts"], errors="coerce").dt.date
        out = out.merge(daily_events, on="trip_date", how="left")
        out["event_count"] = out["event_count"].fillna(0).astype(int)
    elif "event_count" not in out.columns:
        out["event_count"] = 0

    return out


def add_analytics_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create readable analytics features used by summary tables."""
    out = add_time_features(df)
    out = add_congestion_proxy(out)

    if "pickup_ts" in out.columns:
        ts = pd.to_datetime(out["pickup_ts"], errors="coerce")
        out["is_weekend"] = ts.dt.dayofweek.isin([5, 6]).astype(int)
        out["is_rush_hour"] = ts.dt.hour.isin([7, 8, 9, 16, 17, 18, 19]).astype(int)
        out["trip_date"] = ts.dt.date

    out["duration_min"] = pd.to_numeric(out["trip_duration_sec"], errors="coerce") / 60.0

    if "event_count" in out.columns:
        out["event_level"] = pd.cut(
            pd.to_numeric(out["event_count"], errors="coerce").fillna(0),
            bins=[-1, 0, 10, 30, np.inf],
            labels=["none", "low", "medium", "high"],
        )

    if "temp_f" in out.columns:
        out["temp_band"] = pd.cut(
            pd.to_numeric(out["temp_f"], errors="coerce"),
            bins=[-np.inf, 32, 50, 70, np.inf],
            labels=["freezing", "cold", "mild", "warm"],
        )

    if "wind_m_s" in out.columns:
        out["wind_band"] = pd.cut(
            pd.to_numeric(out["wind_m_s"], errors="coerce"),
            bins=[-np.inf, 2, 6, np.inf],
            labels=["low", "moderate", "high"],
        )

    if "humidity" in out.columns:
        out["humidity_band"] = pd.cut(
            pd.to_numeric(out["humidity"], errors="coerce"),
            bins=[-np.inf, 40, 70, np.inf],
            labels=["low", "medium", "high"],
        )

    if {"PULocationID", "DOLocationID"}.issubset(out.columns):
        out["pickup_zone_id"] = pd.to_numeric(out["PULocationID"], errors="coerce").astype("Int64")
        out["dropoff_zone_id"] = pd.to_numeric(out["DOLocationID"], errors="coerce").astype("Int64")
        out["zone_pair"] = (
            out["pickup_zone_id"].astype(str)
            + " -> "
            + out["dropoff_zone_id"].astype(str)
        )
        out["is_airport_trip"] = (
            out["PULocationID"].isin(AIRPORT_LOCATION_IDS)
            | out["DOLocationID"].isin(AIRPORT_LOCATION_IDS)
        ).astype(int)

    if "avg_speed_mph" in out.columns:
        out["congestion_level_text"] = pd.cut(
            pd.to_numeric(out["avg_speed_mph"], errors="coerce"),
            bins=[-np.inf, 8, 16, np.inf],
            labels=["high", "medium", "low"],
        )

    return out


def add_taxi_zone_labels(df: pd.DataFrame, zones: pd.DataFrame | None = None) -> pd.DataFrame:
    """Attach readable pickup/dropoff borough and zone names."""
    if not {"pickup_zone_id", "dropoff_zone_id"}.issubset(df.columns):
        return df
    zones = load_taxi_zone_lookup() if zones is None else zones
    if zones.empty:
        return df

    pickup_zones = zones.rename(
        columns={
            "location_id": "pickup_zone_id",
            "borough": "pickup_borough",
            "zone": "pickup_zone",
            "service_zone": "pickup_service_zone",
        }
    )
    dropoff_zones = zones.rename(
        columns={
            "location_id": "dropoff_zone_id",
            "borough": "dropoff_borough",
            "zone": "dropoff_zone",
            "service_zone": "dropoff_service_zone",
        }
    )

    out = df.merge(
        pickup_zones[
            ["pickup_zone_id", "pickup_borough", "pickup_zone", "pickup_service_zone"]
        ],
        on="pickup_zone_id",
        how="left",
    )
    out = out.merge(
        dropoff_zones[
            ["dropoff_zone_id", "dropoff_borough", "dropoff_zone", "dropoff_service_zone"]
        ],
        on="dropoff_zone_id",
        how="left",
    )
    out["zone_pair_name"] = (
        out["pickup_zone"].fillna("Unknown")
        + " -> "
        + out["dropoff_zone"].fillna("Unknown")
    )
    out["borough_pair"] = (
        out["pickup_borough"].fillna("Unknown")
        + " -> "
        + out["dropoff_borough"].fillna("Unknown")
    )
    return out


def _summary(
    df: pd.DataFrame,
    group_cols: str | list[str],
    min_trips: int = 1,
) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols, dropna=False, observed=True)
        .agg(
            trips=("trip_duration_sec", "size"),
            avg_duration_min=("duration_min", "mean"),
            median_duration_min=("duration_min", "median"),
            avg_distance_miles=("trip_distance", "mean"),
            avg_speed_mph=("avg_speed_mph", "mean"),
            avg_event_count=("event_count", "mean"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["trips"] >= min_trips].copy()
    numeric_cols = grouped.select_dtypes(include=[np.number]).columns
    grouped[numeric_cols] = grouped[numeric_cols].round(3)
    return grouped.sort_values(
        ["trips", "avg_duration_min"], ascending=[False, False]
    ).reset_index(drop=True)


def event_impact_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compare mobility metrics by event intensity."""
    if "event_level" not in df.columns:
        return pd.DataFrame()
    return _summary(df, "event_level")


def weather_impact_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compare mobility metrics across weather bands."""
    tables = []
    for col in ("temp_band", "wind_band", "humidity_band"):
        if col in df.columns:
            part = _summary(df, col)
            part.insert(0, "weather_dimension", col)
            part = part.rename(columns={col: "weather_band"})
            tables.append(part)
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()


def time_mobility_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize trip behavior by hour and weekday/weekend/rush-hour flags."""
    tables = []
    for col in ("hour", "dow", "is_weekend", "is_rush_hour"):
        if col in df.columns:
            part = _summary(df, col)
            part.insert(0, "time_dimension", col)
            part = part.rename(columns={col: "time_value"})
            tables.append(part)
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()


def zone_pair_summary(df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    """Rank pickup/dropoff zone pairs by trip volume and duration."""
    if "zone_pair" not in df.columns:
        return pd.DataFrame()
    data = df.copy()
    for col in ("pickup_zone_id", "dropoff_zone_id"):
        if col in data.columns:
            data = data[~pd.to_numeric(data[col], errors="coerce").isin([264, 265])]
    if "zone_pair_name" in data.columns:
        data = data[~data["zone_pair_name"].astype(str).str.contains("Unknown", case=False, na=False)]

    group_cols = ["zone_pair"]
    for col in (
        "zone_pair_name",
        "borough_pair",
        "pickup_zone_id",
        "pickup_borough",
        "pickup_zone",
        "dropoff_zone_id",
        "dropoff_borough",
        "dropoff_zone",
    ):
        if col in df.columns:
            group_cols.append(col)
    return _summary(data, group_cols, min_trips=5).head(top_n)


def airport_trip_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Compare airport trips against non-airport trips."""
    if "is_airport_trip" not in df.columns:
        return pd.DataFrame()
    return _summary(df, "is_airport_trip")


def build_analytics_tables(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Build all summary tables used by reports and dashboards."""
    return {
        "event_impact": event_impact_summary(df),
        "weather_impact": weather_impact_summary(df),
        "time_mobility": time_mobility_summary(df),
        "zone_pair": zone_pair_summary(df),
        "airport_trip": airport_trip_summary(df),
    }


def save_analytics_tables(
    tables: Dict[str, pd.DataFrame],
    out_dir: Path | str | None = None,
) -> None:
    """Save summary tables as CSV files."""
    output_dir = Path(out_dir) if out_dir else config.OUTPUTS_DIR / "analytics"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        if table.empty:
            logger.warning("Skipping empty analytics table: %s", name)
            continue
        path = output_dir / f"{name}.csv"
        table.to_csv(path, index=False)
        logger.info("Wrote %s", path)


def _table_row(table: pd.DataFrame, column: str, value: object) -> pd.Series | None:
    if table.empty or column not in table.columns:
        return None
    matches = table[table[column].astype(str) == str(value)]
    if matches.empty:
        return None
    return matches.iloc[0]


def build_business_insights(tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create plain-English, PPT-ready insights from analytics tables."""
    insights: list[dict[str, str]] = []

    event = tables.get("event_impact", pd.DataFrame())
    high_event = _table_row(event, "event_level", "high")
    no_event = _table_row(event, "event_level", "none")
    if high_event is not None and no_event is not None:
        high_duration = _safe_float(high_event.get("avg_duration_min"))
        no_duration = _safe_float(no_event.get("avg_duration_min"))
        diff = high_duration - no_duration
        if abs(diff) < 0.5:
            event_takeaway = "not show a meaningful difference in trip delay"
        elif diff > 0:
            event_takeaway = "show slightly longer trip delay"
        else:
            event_takeaway = "show slightly shorter average trip duration"
        insights.append(
            {
                "slide_title": "Event Impact",
                "business_question": "Do citywide events make taxi trips slower?",
                "key_metric": f"High-event days average {_sentence_number(high_duration, 'min')} vs no-event days {_sentence_number(no_duration, 'min')}.",
                "insight": f"Citywide event volume alone does {event_takeaway} in this sample.",
                "why_it_matters": "For better planning, future work should measure events near pickup/dropoff zones instead of only counting all NYC events.",
                "chart_file": "event_impact_duration.png",
                "source_table": "event_impact.csv",
            }
        )

    weather = tables.get("weather_impact", pd.DataFrame())
    if not weather.empty and {"weather_dimension", "weather_band"}.issubset(weather.columns):
        temp = weather[weather["weather_dimension"] == "temp_band"].copy()
        if not temp.empty:
            slowest = temp.sort_values("avg_duration_min", ascending=False).iloc[0]
            fastest = temp.sort_values("avg_duration_min", ascending=True).iloc[0]
            insights.append(
                {
                    "slide_title": "Weather Impact",
                    "business_question": "Does weather change taxi travel time?",
                    "key_metric": f"Slowest temperature band: {slowest['weather_band']} at {_sentence_number(_safe_float(slowest['avg_duration_min']), 'min')}.",
                    "insight": f"Weather changes trip duration, but the gap between {slowest['weather_band']} and {fastest['weather_band']} is smaller than distance and location effects.",
                    "why_it_matters": "Weather is useful context, but business decisions should prioritize distance, zones, and time of day first.",
                    "chart_file": "weather_impact_duration.png",
                    "source_table": "weather_impact.csv",
                }
            )

    time = tables.get("time_mobility", pd.DataFrame())
    if not time.empty and "time_dimension" in time.columns:
        hourly = time[time["time_dimension"] == "hour"].copy()
        if not hourly.empty:
            hourly["time_value"] = pd.to_numeric(hourly["time_value"], errors="coerce")
            slowest = hourly.sort_values("avg_duration_min", ascending=False).iloc[0]
            busiest = hourly.sort_values("trips", ascending=False).iloc[0]
            insights.append(
                {
                    "slide_title": "Time-Based Mobility",
                    "business_question": "When are taxi trips slower or busier?",
                    "key_metric": f"Slowest hour: {int(slowest['time_value']):02d}:00 with {_sentence_number(_safe_float(slowest['avg_duration_min']), 'min')}; busiest hour: {int(busiest['time_value']):02d}:00.",
                    "insight": "Time of day is a strong operational signal for expected delay and demand.",
                    "why_it_matters": "Travelers and dispatchers can use this to plan around slower windows.",
                    "chart_file": "hourly_mobility.png",
                    "source_table": "time_mobility.csv",
                }
            )

    zone = tables.get("zone_pair", pd.DataFrame())
    if not zone.empty:
        top = zone.sort_values("trips", ascending=False).iloc[0]
        route_name = top.get("zone_pair_name", top.get("zone_pair", "Top route"))
        insights.append(
            {
                "slide_title": "Common Travel Corridors",
                "business_question": "Which pickup-dropoff pairs appear most often?",
                "key_metric": f"Top route: {route_name} with {int(_safe_float(top.get('trips'))):,} trips in the sample.",
                "insight": "Taxi demand is concentrated in repeated corridors rather than evenly spread across the city.",
                "why_it_matters": "These corridors are useful for demand planning, fleet positioning, and map storytelling.",
                "chart_file": "top_zone_pairs.png",
                "source_table": "zone_pair.csv",
            }
        )

    airport = tables.get("airport_trip", pd.DataFrame())
    airport_row = _table_row(airport, "is_airport_trip", 1)
    city_row = _table_row(airport, "is_airport_trip", 0)
    if airport_row is not None and city_row is not None:
        airport_duration = _safe_float(airport_row.get("avg_duration_min"))
        city_duration = _safe_float(city_row.get("avg_duration_min"))
        airport_distance = _safe_float(airport_row.get("avg_distance_miles"))
        city_distance = _safe_float(city_row.get("avg_distance_miles"))
        insights.append(
            {
                "slide_title": "Airport Trip Behavior",
                "business_question": "Are airport trips different from regular city trips?",
                "key_metric": f"Airport trips average {_sentence_number(airport_duration, 'min')} and {_sentence_number(airport_distance, 'mi')}; non-airport trips average {_sentence_number(city_duration, 'min')} and {_sentence_number(city_distance, 'mi')}.",
                "insight": "Airport trips are a separate travel pattern, so the model should treat them as a special feature.",
                "why_it_matters": "This improves prediction quality and gives a clear story for route planning.",
                "chart_file": "airport_vs_non_airport.png",
                "source_table": "airport_trip.csv",
            }
        )

    return pd.DataFrame(insights)


def generate_analytics_charts(tables: Dict[str, pd.DataFrame], out_dir: Path) -> None:
    """Generate clean, academic-report friendly charts from analytics summaries."""
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 15,
            "axes.labelsize": 11,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "figure.dpi": 160,
        }
    )

    def clean_axes(ax, grid_axis: str = "y") -> None:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#B8B8B8")
        ax.spines["bottom"].set_color("#B8B8B8")
        ax.grid(axis=grid_axis, color="#E4E4E4", linewidth=0.8)
        ax.set_axisbelow(True)

    def shorten_route(label: str, limit: int = 48) -> str:
        replacements = {
            "Upper East Side": "UES",
            "Upper West Side": "UWS",
            "Lincoln Square": "Lincoln Sq.",
            "Midtown Center": "Midtown Ctr.",
            "North": "N",
            "South": "S",
            "East": "E",
            "West": "W",
        }
        out = str(label)
        for old, new in replacements.items():
            out = out.replace(old, new)
        return out if len(out) <= limit else out[: limit - 1] + "..."

    event = tables.get("event_impact", pd.DataFrame())
    if not event.empty and {"event_level", "avg_duration_min"}.issubset(event.columns):
        order = ["none", "low", "medium", "high"]
        plot = event.copy()
        plot["event_level"] = pd.Categorical(plot["event_level"], categories=order, ordered=True)
        plot = plot.sort_values("event_level")
        plot = plot.dropna(subset=["event_level"])
        x = np.arange(len(plot))
        fig, ax = plt.subplots(figsize=(8.8, 4.8))
        ax.vlines(x, 0, plot["avg_duration_min"], color="#CBD5E1", linewidth=2.4, zorder=1)
        ax.scatter(x, plot["avg_duration_min"], s=95, color="#173B57", edgecolor="white", linewidth=1.2, zorder=2)
        for xi, yi in zip(x, plot["avg_duration_min"]):
            ax.text(xi, yi + 0.25, f"{yi:.1f}", ha="center", va="bottom", fontsize=9.5, color="#173B57")
        ax.set_xticks(x)
        ax.set_xticklabels(plot["event_level"].astype(str))
        ax.set_ylim(0, max(plot["avg_duration_min"]) + 2.0)
        ax.set_title("Average Trip Duration Across Event Levels", pad=12, weight="bold")
        ax.set_xlabel("Event level")
        ax.set_ylabel("Average trip duration (minutes)")
        clean_axes(ax)
        fig.tight_layout()
        fig.savefig(out_dir / "event_impact_duration.png", dpi=160)
        plt.close(fig)

    weather = tables.get("weather_impact", pd.DataFrame())
    if not weather.empty and {"weather_dimension", "weather_band", "avg_duration_min"}.issubset(weather.columns):
        temp = weather[weather["weather_dimension"] == "temp_band"].copy()
        if not temp.empty:
            preferred = ["mild", "cold", "freezing"]
            temp["weather_band"] = pd.Categorical(temp["weather_band"], categories=preferred, ordered=True)
            temp = temp.sort_values("weather_band").dropna(subset=["weather_band"])
            color_map = {"mild": "#F59E0B", "cold": "#2563EB", "freezing": "#93C5FD"}
            colors = [color_map.get(str(b), "#64748B") for b in temp["weather_band"]]
            fig, ax = plt.subplots(figsize=(8.8, 4.8))
            bars = ax.barh(temp["weather_band"].astype(str), temp["avg_duration_min"], color=colors, height=0.55)
            ax.invert_yaxis()
            for bar, val in zip(bars, temp["avg_duration_min"]):
                ax.text(val + 0.15, bar.get_y() + bar.get_height() / 2, f"{val:.1f}", va="center", fontsize=9.5, color="#111827")
            ax.set_title("Average Trip Duration by Temperature Condition", pad=12, weight="bold")
            ax.set_xlabel("Average trip duration (minutes)")
            ax.set_ylabel("Temperature condition")
            ax.set_xlim(0, max(temp["avg_duration_min"]) + 2.2)
            clean_axes(ax, grid_axis="x")
            fig.tight_layout()
            fig.savefig(out_dir / "weather_impact_duration.png", dpi=160)
            plt.close(fig)

    time = tables.get("time_mobility", pd.DataFrame())
    if not time.empty and {"time_dimension", "time_value", "avg_duration_min", "trips"}.issubset(time.columns):
        hourly = time[time["time_dimension"] == "hour"].copy()
        if not hourly.empty:
            hourly["time_value"] = pd.to_numeric(hourly["time_value"], errors="coerce")
            hourly = hourly.sort_values("time_value")
            peak_demand = hourly.loc[hourly["trips"].idxmax()]
            longest_duration = hourly.loc[hourly["avg_duration_min"].idxmax()]
            fig, ax1 = plt.subplots(figsize=(10, 5.4))
            ax2 = ax1.twinx()
            ax2.bar(
                hourly["time_value"],
                hourly["trips"],
                alpha=0.35,
                color="#93C5FD",
                edgecolor="#7DB7E8",
                linewidth=0.4,
                label="Trip count",
                zorder=1,
            )
            ax1.plot(
                hourly["time_value"],
                hourly["avg_duration_min"],
                marker="o",
                markersize=5.5,
                linewidth=2.2,
                color="#C2410C",
                markerfacecolor="#EA580C",
                markeredgecolor="white",
                label="Average duration",
                zorder=3,
            )
            ax1.set_xlabel("Hour of day")
            ax1.set_ylabel("Average trip duration (minutes)", color="#C2410C")
            ax2.set_ylabel("Trip count", color="#2563EB")
            ax1.set_title("Hourly Taxi Demand and Average Trip Duration", pad=12, weight="bold")
            ax1.set_xticks(range(0, 24, 2))
            duration_min = hourly["avg_duration_min"].min()
            duration_max = hourly["avg_duration_min"].max()
            ax1.set_ylim(duration_min - 0.45, duration_max + 0.85)
            ax1.tick_params(axis="y", labelcolor="#C2410C")
            ax2.tick_params(axis="y", labelcolor="#2563EB")
            clean_axes(ax1)
            ax2.grid(False)
            ax1.annotate(
                f"Longest avg duration\n{int(longest_duration['time_value']):02d}:00, {longest_duration['avg_duration_min']:.1f} min",
                xy=(longest_duration["time_value"], longest_duration["avg_duration_min"]),
                xytext=(longest_duration["time_value"] - 6.2, longest_duration["avg_duration_min"] + 0.42),
                arrowprops={"arrowstyle": "->", "color": "#C2410C", "lw": 1.0},
                fontsize=9,
                color="#7C2D12",
                bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#F3D1C4", "alpha": 0.92},
            )
            ax2.annotate(
                f"Peak demand\n{int(peak_demand['time_value']):02d}:00, {int(peak_demand['trips']):,} trips",
                xy=(peak_demand["time_value"], peak_demand["trips"]),
                xytext=(peak_demand["time_value"] + 1.3, peak_demand["trips"] - 1000),
                arrowprops={"arrowstyle": "->", "color": "#2563EB", "lw": 1.0},
                fontsize=9,
                color="#1E3A8A",
                bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": "#BFDBFE", "alpha": 0.92},
            )
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=False)
            fig.tight_layout()
            fig.savefig(out_dir / "hourly_mobility.png", dpi=160)
            plt.close(fig)

    zone = tables.get("zone_pair", pd.DataFrame())
    if not zone.empty and "trips" in zone.columns:
        label_col = "zone_pair_name" if "zone_pair_name" in zone.columns else "zone_pair"
        top = zone.sort_values("trips", ascending=False).head(8).copy()
        if {"pickup_zone", "dropoff_zone"}.issubset(top.columns):
            top["route_pair"] = top["pickup_zone"].fillna("Unknown") + " -> " + top["dropoff_zone"].fillna("Unknown")
            label_col = "route_pair"
        top["route_label"] = top[label_col].map(shorten_route)
        fig, ax = plt.subplots(figsize=(10, 5.4))
        bars = ax.barh(top["route_label"][::-1], top["trips"][::-1], color="#4C1D95", height=0.58)
        for bar, val in zip(bars, top["trips"][::-1]):
            ax.text(val + max(top["trips"]) * 0.015, bar.get_y() + bar.get_height() / 2, f"{int(val):,}", va="center", fontsize=9.5, color="#111827")
        ax.set_title("Top Pickup-Dropoff Zone Pairs", pad=12, weight="bold")
        ax.set_xlabel("Trips in sample")
        ax.set_ylabel("")
        ax.set_xlim(0, max(top["trips"]) * 1.14)
        clean_axes(ax, grid_axis="x")
        fig.tight_layout()
        fig.savefig(out_dir / "top_zone_pairs.png", dpi=160)
        plt.close(fig)

    airport = tables.get("airport_trip", pd.DataFrame())
    if not airport.empty and {"is_airport_trip", "avg_duration_min", "avg_distance_miles"}.issubset(airport.columns):
        plot = airport.copy()
        plot["trip_type"] = plot["is_airport_trip"].map({0: "Non-airport", 1: "Airport"}).fillna(airport["is_airport_trip"].astype(str))
        order = ["Non-airport", "Airport"]
        plot["trip_type"] = pd.Categorical(plot["trip_type"], categories=order, ordered=True)
        plot = plot.sort_values("trip_type")
        fig, ax = plt.subplots(figsize=(8.8, 4.8))
        x = np.arange(len(plot))
        width = 0.35
        duration_bars = ax.bar(x - width / 2, plot["avg_duration_min"], width, label="Avg duration (min)", color="#F97316")
        distance_bars = ax.bar(x + width / 2, plot["avg_distance_miles"], width, label="Avg distance (mi)", color="#2563EB")
        for bars in (duration_bars, distance_bars):
            for bar in bars:
                val = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, val + 0.55, f"{val:.1f}", ha="center", va="bottom", fontsize=9.5)
        ax.set_xticks(x)
        ax.set_xticklabels(plot["trip_type"])
        ax.set_ylabel("Average value")
        ax.set_title("Airport vs Non-Airport Trip Characteristics", pad=12, weight="bold")
        ax.set_ylim(0, max(plot["avg_duration_min"].max(), plot["avg_distance_miles"].max()) + 5)
        ax.legend(frameon=False, loc="upper left")
        clean_axes(ax)
        fig.tight_layout()
        fig.savefig(out_dir / "airport_vs_non_airport.png", dpi=160)
        plt.close(fig)


def save_business_insights(
    insights: pd.DataFrame,
    tables: Dict[str, pd.DataFrame],
    out_dir: Path | str | None = None,
) -> None:
    """Save presentation-ready insight artifacts."""
    output_dir = Path(out_dir) if out_dir else config.OUTPUTS_DIR / "analytics" / "insights"
    output_dir.mkdir(parents=True, exist_ok=True)

    if insights.empty:
        logger.warning("No business insights generated.")
        return

    insights_csv = output_dir / "business_insights.csv"
    insights_json = output_dir / "business_insights.json"
    insights_md = output_dir / "business_insights.md"

    insights.to_csv(insights_csv, index=False)
    insights_json.write_text(
        json.dumps(insights.to_dict(orient="records"), indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Urban Mobility Business Insights",
        "",
        "These insights are written for presentation slides. Each item is a business question, one key metric, and one takeaway.",
        "",
    ]
    for idx, row in insights.iterrows():
        lines.extend(
            [
                f"## {idx + 1}. {row['slide_title']}",
                "",
                f"**Question:** {row['business_question']}",
                "",
                f"**Key metric:** {row['key_metric']}",
                "",
                f"**Insight:** {row['insight']}",
                "",
                f"**Why it matters:** {row['why_it_matters']}",
                "",
                f"**Suggested chart:** `{row['chart_file']}`",
                "",
            ]
        )
    insights_md.write_text("\n".join(lines), encoding="utf-8")
    generate_analytics_charts(tables, output_dir)

    logger.info("Wrote %s", insights_csv)
    logger.info("Wrote %s", insights_json)
    logger.info("Wrote %s", insights_md)


def run_analytics(max_rows: int | None = 100_000) -> Dict[str, pd.DataFrame]:
    """Load raw datasets, build analytics features, and save CSV summaries."""
    config.ensure_output_dirs()
    taxi = preprocess_taxi_for_analytics(load_taxi_for_analytics(max_rows=max_rows))
    weather = preprocess_weather_df(load_weather_pandas())
    events = preprocess_events_df(load_events_pandas())
    merged = merge_context_for_analytics(taxi, weather, events)
    enriched = add_analytics_features(merged)
    enriched = add_taxi_zone_labels(enriched)
    tables = build_analytics_tables(enriched)
    save_analytics_tables(tables)
    insights = build_business_insights(tables)
    save_business_insights(insights, tables)
    return tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate detailed mobility analytics CSVs.")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=100_000,
        help="Taxi rows to sample for analytics. Use 0 for all rows.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()
    max_rows = args.max_rows if args.max_rows > 0 else None
    run_analytics(max_rows=max_rows)


if __name__ == "__main__":
    main()
