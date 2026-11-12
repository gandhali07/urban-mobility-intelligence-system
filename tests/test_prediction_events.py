"""Tests for event-date handling in the prediction interface."""
import unittest
from datetime import datetime

import pandas as pd

from predict_trip import count_events_on_date


class PredictionEventTests(unittest.TestCase):
    def test_counts_events_using_raw_start_date_column(self):
        events = pd.DataFrame({
            "Start Date/Time": [
                "2023-02-24 08:00:00",
                "2023-02-24 18:30:00",
                "2023-02-25 09:00:00",
            ]
        })
        self.assertEqual(count_events_on_date(events, datetime(2023, 2, 24, 17, 30)), 2)

    def test_counts_preprocessed_event_date(self):
        events = pd.DataFrame({"event_date": pd.to_datetime(["2023-02-24", "2023-02-25"])})
        self.assertEqual(count_events_on_date(events, datetime(2023, 2, 24)), 1)

    def test_unknown_schema_is_not_silently_zero(self):
        with self.assertRaisesRegex(ValueError, "recognized date column"):
            count_events_on_date(pd.DataFrame({"name": ["Event"]}), datetime(2023, 2, 24))

    def test_unparseable_dates_are_not_silently_zero(self):
        with self.assertRaisesRegex(ValueError, "no parseable dates"):
            count_events_on_date(pd.DataFrame({"event_date": ["not a date"]}), datetime(2023, 2, 24))


if __name__ == "__main__":
    unittest.main()
