import json
import subprocess
from datetime import date
from unittest.mock import patch

from src.fetch_sources import (
    Event,
    Message,
    _run_skill,
    compute_week_window,
    fetch_calendar_range,
    fetch_gmail,
)


def test_run_skill_parses_json_stdout():
    fake_result = subprocess.CompletedProcess(
        args=["x"], returncode=0,
        stdout=json.dumps([{"a": 1}, {"a": 2}]),
        stderr="",
    )
    with patch("subprocess.run", return_value=fake_result) as mock_run:
        result = _run_skill("/fake/path", ["--arg", "v"])
    assert result == [{"a": 1}, {"a": 2}]
    mock_run.assert_called_once()
    called_args = mock_run.call_args[0][0]
    assert called_args == ["/fake/path", "--arg", "v"]


def test_week_window_from_thursday():
    # Thursday May 21 2026 → window should start Fri May 22
    today = date(2026, 5, 21)
    start, end, horizon = compute_week_window(today)
    assert start == date(2026, 5, 22)
    assert end == date(2026, 5, 28)
    assert horizon == date(2026, 6, 18)


def test_week_window_from_friday():
    # Friday counts as the start day itself
    today = date(2026, 5, 22)
    start, end, horizon = compute_week_window(today)
    assert start == date(2026, 5, 22)
    assert end == date(2026, 5, 28)


def test_week_window_from_saturday():
    # Saturday May 23 → next Friday is May 29
    today = date(2026, 5, 23)
    start, end, _ = compute_week_window(today)
    assert start == date(2026, 5, 29)
    assert end == date(2026, 6, 4)


def test_fetch_calendar_range_calls_skill_per_day_and_tags_source():
    # 3-day range = 3 skill calls
    fake_responses = [
        [{"title": "Day1 evt", "start": "9:00 AM", "end": "10:00 AM"}],
        [],  # day 2 empty
        [{"title": "Day3 evt", "start": "all-day", "end": "all-day", "location": "Home"}],
    ]
    with patch("src.fetch_sources._run_skill", side_effect=fake_responses) as mock:
        events = fetch_calendar_range(
            calendar_id="cal@x",
            start=date(2026, 5, 22),
            end=date(2026, 5, 24),
            source_tag="general",
            exclude_recurring=False,
        )
    assert mock.call_count == 3
    assert len(events) == 2
    assert events[0].title == "Day1 evt"
    assert events[0].date == "2026-05-22"
    assert events[0].source == "general"
    assert events[1].title == "Day3 evt"
    assert events[1].location == "Home"


def test_fetch_calendar_range_passes_exclude_recurring_flag():
    with patch("src.fetch_sources._run_skill", return_value=[]) as mock:
        fetch_calendar_range(
            calendar_id="cal@x",
            start=date(2026, 5, 22),
            end=date(2026, 5, 22),
            source_tag="general",
            exclude_recurring=True,
        )
    # one call (one-day range), with the flag in args
    called_args = mock.call_args[0][1]
    assert "--exclude-recurring" in called_args


def test_fetch_gmail_basic(load_fixture):
    fixture = load_fixture("gmail_dalton.json")
    with patch("src.fetch_sources._run_skill", return_value=fixture) as mock:
        msgs, hit_cap = fetch_gmail(
            account="dalton",
            query="newer_than:7d -category:promotions",
            max_results=50,
            label_id=None,
        )
    assert len(msgs) == 2
    assert hit_cap is False
    assert msgs[0].id == "abc1"
    assert msgs[0].subject == "Appt reminder"
    assert msgs[0].account == "dalton"
    called_args = mock.call_args[0][1]
    assert "--account" in called_args
    assert "dalton" in called_args
    assert "--query" in called_args
    assert "--max-results" in called_args
    assert "50" in called_args


def test_fetch_gmail_hits_volume_cap(load_fixture):
    # fixture has 60 items but we ask for 50; skill returns all 60 (it doesn't truncate),
    # so the helper takes 50 and flags cap-hit
    fixture = load_fixture("gmail_volume_cap.json")
    with patch("src.fetch_sources._run_skill", return_value=fixture):
        msgs, hit_cap = fetch_gmail(
            account="dalton",
            query="x",
            max_results=50,
            label_id=None,
        )
    assert len(msgs) == 50
    assert hit_cap is True


def test_fetch_gmail_with_label_id_uses_label_query(load_fixture):
    fixture = load_fixture("gmail_kid_school.json")
    with patch("src.fetch_sources._run_skill", return_value=fixture) as mock:
        msgs, hit_cap = fetch_gmail(
            account="dalton",
            query="newer_than:7d",
            max_results=50,
            label_id="Label_1234567890123456789",
        )
    assert len(msgs) == 2
    assert msgs[0].account == "kid_school"  # tagged by helper since label_id was set
    called_args = mock.call_args[0][1]
    # Confirm the label was included by chaining onto the query
    # (we use Gmail's label: search syntax; the label ID must appear in the --query arg)
    query_idx = called_args.index("--query") + 1
    full_query = called_args[query_idx]
    assert "label:Label_1234567890123456789" in full_query or "Label_1234567890123456789" in full_query
