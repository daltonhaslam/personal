import json
import subprocess
from unittest.mock import patch
from src.fetch_sources import _run_skill


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


from datetime import date
from src.fetch_sources import compute_week_window


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
