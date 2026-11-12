"""Shared, date-level event features for training and prediction."""
from __future__ import annotations

import pandas as pd


def _date_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    return next((col for col in candidates if col in df.columns), None)


def daily_active_event_counts(
    events: pd.DataFrame, start_col: str | None = None
) -> pd.DataFrame:
    """Count each event on every calendar day it overlaps, inclusive.

    A missing end date is treated as a one-day event. Invalid end dates
    preceding the start date are also treated as one-day events.
    """
    empty = pd.DataFrame({
        "event_day": pd.Series(dtype="datetime64[ns]"),
        "event_count": pd.Series(dtype="int64"),
    })
    if events.empty:
        return empty

    start_col = start_col if start_col in events.columns else _date_column(
        events, ("event_date", "Start Date/Time", "start_date_time", "date")
    )
    if start_col is None:
        raise ValueError("Event data has no recognized start date column.")

    end_col = _date_column(
        events, ("End Date/Time", "end_date_time", "event_end", "end_date")
    )
    starts = pd.to_datetime(events[start_col], errors="coerce")
    if starts.notna().sum() == 0:
        raise ValueError(f"Event start date column {start_col!r} contains no parseable dates.")
    ends = (
        pd.to_datetime(events[end_col], errors="coerce")
        if end_col is not None
        else pd.Series(pd.NaT, index=events.index, dtype="datetime64[ns]")
    )
    days: list[pd.Timestamp] = []
    for start, end in zip(starts, ends):
        if pd.isna(start):
            continue
        first = start.normalize()
        last = end.normalize() if pd.notna(end) and end >= start else first
        days.extend(pd.date_range(first, last, freq="D"))
    if not days:
        return empty
    counts = pd.Series(days).value_counts().sort_index()
    return pd.DataFrame({
        "event_day": counts.index,
        "event_count": counts.to_numpy(dtype="int64"),
    }).reset_index(drop=True)


def active_event_count_for_date(events: pd.DataFrame, trip_dt) -> int:
    daily = daily_active_event_counts(events)
    if daily.empty:
        return 0
    day = pd.Timestamp(trip_dt).normalize()
    match = daily.loc[daily["event_day"] == day, "event_count"]
    return int(match.iloc[0]) if not match.empty else 0
