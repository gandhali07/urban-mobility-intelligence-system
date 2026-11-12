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

    def test_multiday_events_count_on_each_active_day(self):
        events = pd.DataFrame({
            "start_date_time": ["2023-02-23 10:00", "2023-02-24 15:00"],
            "end_date_time": ["2023-02-25 18:00", "2023-02-24 19:00"],
        })
        self.assertEqual(count_events_on_date(events, datetime(2023, 2, 24)), 2)
        self.assertEqual(count_events_on_date(events, datetime(2023, 2, 25)), 1)
        self.assertEqual(count_events_on_date(events, datetime(2023, 2, 26)), 0)

    def test_unknown_schema_is_not_silently_zero(self):
        with self.assertRaisesRegex(ValueError, "recognized start date column"):
            count_events_on_date(pd.DataFrame({"name": ["Event"]}), datetime(2023, 2, 24))

    def test_unparseable_dates_are_not_silently_zero(self):
        with self.assertRaisesRegex(ValueError, "no parseable dates"):
            count_events_on_date(pd.DataFrame({"event_date": ["not a date"]}), datetime(2023, 2, 24))


if __name__ == "__main__":
    unittest.main()
