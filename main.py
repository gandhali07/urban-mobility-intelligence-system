"""
Urban Mobility Intelligence System — main pipeline entrypoint.

Run from project root:

    python main.py --step all
    python main.py --step demo_map
    python main.py --step load preprocess merge features cluster model shap map

Each step can be run separately; `--step all` runs the full path (needs data in data/raw/).
"""
from __future__ import annotations

import argparse
import logging
from src import config
from src.clustering import run_dbscan_hotspots
from src.data_loading import (
    create_spark_session,
    load_events_pandas,
    load_taxi_spark,
    load_weather_pandas,
)
from src.feature_engineering import (
    add_congestion_proxy,
    bin_congestion_level,
    build_model_matrix,
)
from src.map_visualization import build_demo_map, build_urban_mobility_map, sample_demo_data
from src.merging import merge_taxi_weather_events_spark, merged_spark_to_pandas
from src.modeling import save_model_artifacts, train_xgboost_model
from src.preprocessing import preprocess_events_df, preprocess_taxi_spark, preprocess_weather_df
from src.shap_explainability import explain_model

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

AFTER_TRIP_FEATURES = [
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
]


def step_demo_map() -> None:
    config.ensure_output_dirs()
    logger.info("STEP: demo_map - generating sample Folium output")
    path = config.MAPS_DIR / "urban_mobility_demo.html"
    build_demo_map(out_path=path)
    logger.info("Open in browser: %s", path.resolve())


def step_load():
    spark = create_spark_session()
    taxi = load_taxi_spark(spark)
    weather = load_weather_pandas()
    events = load_events_pandas()
    return spark, taxi, weather, events


def run_pipeline(max_rows: int | None, target: str) -> None:
    config.ensure_output_dirs()
    spark, taxi, weather, events = step_load()
    try:
        logger.info("STEP: preprocess")
        taxi = preprocess_taxi_spark(taxi)
        weather = preprocess_weather_df(weather)
        events = preprocess_events_df(events)

        logger.info("STEP: merge (Spark)")
        merged = merge_taxi_weather_events_spark(taxi, weather, events, spark)
        pdf = merged_spark_to_pandas(merged, max_rows=max_rows)

        logger.info("STEP: feature engineering + clustering (pandas)")
        pdf = add_congestion_proxy(pdf)
        min_samples = max(3, min(15, max(1, len(pdf) // 3)))
        pdf, centers = run_dbscan_hotspots(pdf, min_samples=min_samples)
        pdf = bin_congestion_level(pdf)

        if target == "trip_duration_sec":
            task: str = "regression"
            y_col = "trip_duration_sec"
        else:
            task = "classification"
            y_col = "congestion_level"

        exclude = ["avg_speed_mph"] if y_col == "congestion_level" else AFTER_TRIP_FEATURES
        X, y, feat_names = build_model_matrix(
            pdf, target_col=y_col, exclude_features=exclude
        )
        if task == "classification":
            y = y.astype(int)

        logger.info("STEP: model (%s, target=%s)", task, y_col)
        if "pickup_ts" not in pdf.columns:
            raise ValueError("pickup_ts is required for chronological evaluation")
        timestamps = pdf.loc[X.index, "pickup_ts"]
        model, metrics, X_train, X_test, y_train, y_test = train_xgboost_model(
            X, y, task=task, timestamps=timestamps
        )
        model_path = config.MODELS_DIR / "xgboost_model.json"
        meta_path = config.MODELS_DIR / "xgboost_model_meta.json"
        save_model_artifacts(model, feat_names, metrics, model_path, meta_path)

        logger.info("STEP: SHAP")
        sample_X = X_test.head(min(400, len(X_test)))
        explain_model(model, sample_X, figures_dir=config.FIGURES_DIR)

        logger.info("STEP: map")
        heat_cols = [c for c in ("pickup_lat", "pickup_lon") if c in pdf.columns]
        heatmap_df = (
            pdf[heat_cols].dropna()
            if len(heat_cols) == 2
            else sample_demo_data()["heatmap_points"]
        )
        if centers.empty:
            hotspots_for_map = sample_demo_data()["hotspots_df"]
        else:
            hotspots_for_map = centers
            if "hotspot_cluster" in pdf.columns and "congestion_level" in pdf.columns:
                sev = (
                    pdf.groupby("hotspot_cluster")
                    .agg(congestion_level=("congestion_level", "mean"))
                    .reset_index()
                )
                hotspots_for_map = hotspots_for_map.merge(
                    sev, on="hotspot_cluster", how="left"
                )
                hotspots_for_map["congestion_level"] = (
                    hotspots_for_map["congestion_level"].round().fillna(1).astype(int)
                )
        map_path = config.MAPS_DIR / "urban_mobility_map.html"
        build_urban_mobility_map(
            hotspots_df=hotspots_for_map,
            heatmap_points=heatmap_df,
            events_df=events if not events.empty else sample_demo_data()["events_df"],
            out_path=map_path,
        )
        logger.info("Map saved: %s", map_path.resolve())
    finally:
        spark.stop()
        logger.info("Spark session stopped.")


def parse_args():
    p = argparse.ArgumentParser(description="Urban Mobility Intelligence pipeline")
    p.add_argument(
        "--step",
        nargs="+",
        default=["all"],
        help="Steps: all | demo_map | load | ... (pass multiple for future extensions)",
    )
    p.add_argument(
        "--max-rows",
        type=int,
        default=50_000,
        help="Max rows to pull from Spark after merge (None = full collect; may OOM).",
    )
    p.add_argument(
        "--target",
        choices=["trip_duration_sec", "congestion_level"],
        default="trip_duration_sec",
        help="Regression on duration or classification on binned congestion.",
    )
    return p.parse_args()


def main():
    args = parse_args()
    steps = [s.lower() for s in args.step]
    if "demo_map" in steps:
        step_demo_map()
        if steps == ["demo_map"]:
            return
    if "all" in steps:
        mr = args.max_rows if args.max_rows > 0 else None
        run_pipeline(max_rows=mr, target=args.target)
    elif "load" in steps:
        logger.info("Running load-only example...")
        spark, taxi, weather, events = step_load()
        logger.info("Taxi schema: %s", taxi.columns)
        spark.stop()


if __name__ == "__main__":
    main()
