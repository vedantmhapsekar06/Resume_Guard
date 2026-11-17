import calendar
import re
from datetime import datetime, timedelta

from dateutil import parser as date_parser

from backend.config import GAP_THRESHOLD_DAYS, OVERLAP_THRESHOLD_DAYS

_PRESENT = ("present", "current", "ongoing", "now", "till date", "to date", "today")
_YEAR_ONLY = re.compile(r"^\s*((?:19|20)\d{2})\s*$")
_ANY_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def _end_of_month(dt: datetime) -> datetime:
    return dt.replace(day=calendar.monthrange(dt.year, dt.month)[1])


def parse_date_string(date_str: str, is_end: bool = False):
    """
    Parses a loose date like 'Jan 2020', '2020', 'Present'. Returns a datetime or None.

    Precision matters for durations and gaps:
      - a bare year as a START means 1 Jan, as an END means 31 Dec (otherwise
        '2019 - 2020' / '2021 - 2022' would show a fake 12-month gap);
      - 'Mar 2022' as an END means the last day of March.
    'Present' resolves to today. Dates in the future are capped at today.
    """
    if not date_str or not isinstance(date_str, str):
        return None

    cleaned = date_str.strip().lower()
    today = datetime.today()
    if cleaned in _PRESENT:
        return today

    result = None
    m = _YEAR_ONLY.match(cleaned)
    if m:
        year = int(m.group(1))
        result = datetime(year, 12, 31) if is_end else datetime(year, 1, 1)
    else:
        try:
            result = date_parser.parse(date_str, default=datetime(1900, 1, 1))
            if result.year == 1900:   # no year recognised
                result = None
            elif is_end:
                result = _end_of_month(result)
        except (ValueError, OverflowError):
            result = None

        if result is None:   # e.g. 'Summer 2021'
            y = _ANY_YEAR.search(cleaned)
            if y:
                year = int(y.group(1))
                result = datetime(year, 12, 31) if is_end else datetime(year, 1, 1)

    if result and result > today:
        result = today
    return result


def _period(job: dict):
    start = parse_date_string(job.get("start_date", ""), is_end=False)
    end = parse_date_string(job.get("end_date", ""), is_end=True)
    if start and end and end >= start:
        return start, end
    return None


def calculate_duration_years(start_str: str, end_str: str) -> float:
    """Returns duration in years (rounded to 1 decimal) between two date strings."""
    start = parse_date_string(start_str, is_end=False)
    end = parse_date_string(end_str, is_end=True)

    if not start or not end or end < start:
        return 0.0

    return round((end - start).days / 365.25, 1)


def merge_periods(periods: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Union of date ranges: overlapping/nested periods are counted once."""
    merged: list[list[datetime]] = []
    for start, end in sorted(periods, key=lambda p: p[0]):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def total_years(work_history: list[dict]) -> float:
    """Total calendar time worked, with overlapping jobs counted once."""
    periods = [p for p in (_period(j) for j in work_history) if p]
    merged = merge_periods(periods)
    days = sum((e - s).days for s, e in merged)
    return round(days / 365.25, 1)


def detect_gaps_and_overlaps(work_history: list[dict]) -> list[str]:
    """
    work_history: list of dicts with 'start_date' and 'end_date' (raw strings).
    Returns human-readable risk flags for employment gaps or overlapping roles.

    Compares each role to the LATEST end date seen so far (not just the previous role),
    so a short role nested inside a long one is not mistaken for a gap.
    """
    flags = []
    periods = []
    for job in work_history:
        p = _period(job)
        if p:
            periods.append((p[0], p[1], job.get("title") or "Unknown role"))

    periods.sort(key=lambda x: x[0])
    if not periods:
        return flags

    run_end, run_title = periods[0][1], periods[0][2]
    for start, end, title in periods[1:]:
        delta = (start - run_end).days
        if delta > GAP_THRESHOLD_DAYS:
            flags.append(
                f"Employment gap of ~{round(delta / 30)} months between '{run_title}' and '{title}'"
            )
        elif delta < -OVERLAP_THRESHOLD_DAYS:
            flags.append(f"Overlapping dates between '{run_title}' and '{title}'")

        if end > run_end:
            run_end, run_title = end, title

    return flags
