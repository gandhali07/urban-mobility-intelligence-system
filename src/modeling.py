"""
Train XGBoost models for trip duration or congestion level.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Literal, Tuple

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier, XGBRegressor

from src import config

logger = logging.getLogger(__name__)

TaskType = Literal["regression", "classification"]


def train_xgboost_model(
    X: pd.DataFrame,
    y: pd.Series,
    task: TaskType = "regression",
    test_size: float = 0.2,
    random_state: int | None = None,
    timestamps: pd.Series | None = None,
) -> Tuple[object, dict, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Train/test split and fit XGBoost. Returns model, metrics dict, X_train, X_test, y_train, y_test.
    """
    rs = random_state if random_state is not None else config.RANDOM_STATE
    if X.columns.duplicated().any():
        logger.warning("X has duplicate column names; keeping first occurrence for XGBoost.")
        X = X.loc[:, ~X.columns.duplicated(keep="first")]
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    if timestamps is not None:
        # Keep time out of model features; use it only to order the split.
        times = pd.to_datetime(timestamps.reindex(X.index), errors="coerce")
        if times.isna().any():
            raise ValueError("Chronological split requires a valid pickup timestamp for every row")
        order = times.sort_values(kind="stable").index
        X_sorted, y_sorted = X.loc[order], y.loc[order]
        cut = int(len(X_sorted) * (1 - test_size))
        if cut <= 0 or cut >= len(X_sorted):
            raise ValueError("Not enough rows for the requested chronological split")
        X_train, X_test = X_sorted.iloc[:cut], X_sorted.iloc[cut:]
        y_train, y_test = y_sorted.iloc[:cut], y_sorted.iloc[cut:]
        # Same timestamp on both sides can make temporal evaluation ambiguous.
        train_end = times.loc[X_train.index].max()
        test_start = times.loc[X_test.index].min()
        if train_end >= test_start:
            raise ValueError("Train/test boundary contains equal timestamps; use a date-based cutoff")
        logger.info("Chronological split: train through %s; test from %s", train_end, test_start)
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=rs
        )
    # Learn imputation values on training rows only to avoid test-set leakage.
    X_train = X_train.apply(pd.to_numeric, errors="coerce").astype(float)
    X_test = X_test.apply(pd.to_numeric, errors="coerce").astype(float)
    train_medians = X_train.median().fillna(0.0)
    X_train = X_train.fillna(train_medians)
    X_test = X_test.fillna(train_medians)

    if task == "regression":
        dummy = DummyRegressor(strategy="mean")
        dummy.fit(X_train, y_train)
        dummy_pred = dummy.predict(X_test)

        linear = LinearRegression()
        linear.fit(X_train, y_train)
        linear_pred = linear.predict(X_test)

        model = XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=rs,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        metrics = {
            "task": "regression",
            "mae": float(mean_absolute_error(y_test, pred)),
            "r2": float(r2_score(y_test, pred)),
            "baseline_mean_mae": float(mean_absolute_error(y_test, dummy_pred)),
            "baseline_mean_r2": float(r2_score(y_test, dummy_pred)),
            "baseline_linear_mae": float(mean_absolute_error(y_test, linear_pred)),
            "baseline_linear_r2": float(r2_score(y_test, linear_pred)),
        }
    else:
        dummy = DummyClassifier(strategy="most_frequent", random_state=rs)
        dummy.fit(X_train, y_train)
        dummy_pred = dummy.predict(X_test)

        model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=rs,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        metrics = {
            "task": "classification",
            "accuracy": float((pred == y_test.values).mean()),
            "baseline_most_frequent_accuracy": float((dummy_pred == y_test.values).mean()),
        }

    logger.info("Model metrics: %s", metrics)
    return model, metrics, X_train, X_test, y_train, y_test


def save_model_artifacts(
    model: object,
    feature_names: List[str],
    metrics: dict,
    model_path: Path,
    meta_path: Path,
) -> None:
    """Persist booster and small JSON sidecar with features + metrics."""
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(model_path))
    meta = {"feature_names": feature_names, "metrics": metrics}
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Saved model to %s", model_path)
