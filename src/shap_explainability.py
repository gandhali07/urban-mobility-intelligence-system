"""
SHAP explanations for tree-based XGBoost models.
"""
from __future__ import annotations

import logging
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src import config

logger = logging.getLogger(__name__)

# Reduce SHAP plotting noise in terminal output for demos.
warnings.filterwarnings(
    "ignore",
    message="The NumPy global RNG was seeded by calling `np.random.seed`.*",
    category=FutureWarning,
)


def _compute_shap_values(model, X_sample: pd.DataFrame) -> np.ndarray:
    """
    Prefer TreeExplainer (fast). XGBoost 3.x sometimes stores base_score in a form
    SHAP's parser rejects ('[1.815E3]'); then fall back to PermutationExplainer.
    """
    try:
        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(X_sample)
        if isinstance(sv, list):
            sv = sv[1] if len(sv) > 1 else sv[0]
        return np.asarray(sv)
    except (ValueError, TypeError) as e:
        msg = str(e).lower()
        if (
            "base_score" in msg
            or "could not convert string to float" in msg
            or "learner_model_param" in msg
        ):
            logger.warning(
                "TreeExplainer failed on this XGBoost/SHAP combo (%s); "
                "using PermutationExplainer (slower, same semantics).",
                e,
            )
        else:
            logger.warning("TreeExplainer failed (%s); using PermutationExplainer.", e)

    bg = X_sample
    if len(X_sample) > 200:
        bg = X_sample.sample(200, random_state=config.RANDOM_STATE)
    explainer = shap.PermutationExplainer(model.predict, bg)
    out = explainer(X_sample)
    return np.asarray(out.values)


def explain_model(
    model,
    X_sample: pd.DataFrame,
    figures_dir: Path | None = None,
    max_display: int = 12,
) -> None:
    """
    Compute SHAP summaries and save beeswarm + bar plots to figures_dir.
    X_sample should be a small but representative subset for speed.
    """
    figures_dir = figures_dir or config.FIGURES_DIR
    figures_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Computing SHAP values for %s rows...", len(X_sample))
    shap_values = _compute_shap_values(model, X_sample)

    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_sample, max_display=max_display, show=False)
    p1 = figures_dir / "shap_summary_beeswarm.png"
    plt.tight_layout()
    plt.savefig(p1, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Wrote %s", p1)

    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_sample, plot_type="bar", max_display=max_display, show=False)
    p2 = figures_dir / "shap_summary_bar.png"
    plt.tight_layout()
    plt.savefig(p2, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Wrote %s", p2)
