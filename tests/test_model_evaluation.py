"""Synthetic regression checks; run: python -m unittest discover -s tests -v."""
import unittest

import numpy as np
import pandas as pd

from src.modeling import train_xgboost_model


class ChronologicalEvaluationTests(unittest.TestCase):
    def setUp(self):
        n = 40
        self.X = pd.DataFrame({
            "trip_distance": np.linspace(1, 12, n),
            "hour": np.arange(n) % 24,
        })
        self.X.loc[0, "trip_distance"] = np.nan
        self.X.loc[35, "trip_distance"] = np.nan
        self.y = pd.Series(np.linspace(180, 1200, n))
        self.timestamps = pd.Series(
            pd.date_range("2023-02-01", periods=n, freq="h")
        )

    def test_temporal_split_and_training_only_imputation(self):
        _, metrics, X_train, X_test, _, _ = train_xgboost_model(
            self.X, self.y, timestamps=self.timestamps, test_size=0.2
        )
        self.assertEqual(len(X_train), 32)
        self.assertEqual(len(X_test), 8)
        self.assertLess(
            self.timestamps.loc[X_train.index].max(),
            self.timestamps.loc[X_test.index].min(),
        )
        self.assertFalse(X_train.isna().any().any())
        self.assertFalse(X_test.isna().any().any())
        self.assertAlmostEqual(
            X_test.loc[35, "trip_distance"],
            self.X.loc[X_train.index, "trip_distance"].median(),
        )
        self.assertIn("mae", metrics)

    def test_missing_timestamps_rejected(self):
        times = self.timestamps.copy()
        times.iloc[3] = pd.NaT
        with self.assertRaisesRegex(ValueError, "valid pickup timestamp"):
            train_xgboost_model(self.X, self.y, timestamps=times)

    def test_invalid_test_size_rejected(self):
        with self.assertRaisesRegex(ValueError, "test_size"):
            train_xgboost_model(self.X, self.y, timestamps=self.timestamps, test_size=1.0)


if __name__ == "__main__":
    unittest.main()
