"""Pull data from Google Calendar, Gmail, and Todoist into a Context.

All I/O goes through `_run_skill`, which subprocesses out to the existing
bash skills under Personal/skills/. Tests monkeypatch this helper instead
of `subprocess.run` directly.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.constants import GCAL_FETCH


@dataclass
class Event:
    title: str
    date: str          # YYYY-MM-DD
    start: str         # "5:00 PM" or "all-day"
    end: str           # "5:30 PM" or "all-day"
    location: str = ""
    source: str = ""   # "general", "meals", "personal", "school"


@dataclass
class Message:
    id: str
    subject: str
    sender: str
    snippet: str
    date: str
    account: str = ""  # "dalton", "maggie", or "kid_school"


@dataclass
class Task:
    id: str
    content: str
    description: str = ""
    deadline: str = ""  # YYYY-MM-DD or ""
    project_id: str = ""


@dataclass
class Context:
    week_start: date
    week_end: date
    horizon_end: date
    general_events: list[Event] = field(default_factory=list)
    meal_events_last: list[Event] = field(default_factory=list)
    personal_events: list[Event] = field(default_factory=list)
    school_events: list[Event] = field(default_factory=list)
    dalton_gmail: list[Message] = field(default_factory=list)
    maggie_gmail: list[Message] = field(default_factory=list)
    kid_school_emails: list[Message] = field(default_factory=list)
    meals_library: list[Task] = field(default_factory=list)
    date_night_ideas: list[Task] = field(default_factory=list)
    screen_time_ideas: list[Task] = field(default_factory=list)
    upcoming_deadlines: list[Task] = field(default_factory=list)
    inbox_volume_flag: bool = False

    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict for context.json."""
        return {
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "horizon_end": self.horizon_end.isoformat(),
            "general_events": [e.__dict__ for e in self.general_events],
            "meal_events_last": [e.__dict__ for e in self.meal_events_last],
            "personal_events": [e.__dict__ for e in self.personal_events],
            "school_events": [e.__dict__ for e in self.school_events],
            "dalton_gmail": [m.__dict__ for m in self.dalton_gmail],
            "maggie_gmail": [m.__dict__ for m in self.maggie_gmail],
            "kid_school_emails": [m.__dict__ for m in self.kid_school_emails],
            "meals_library": [t.__dict__ for t in self.meals_library],
            "date_night_ideas": [t.__dict__ for t in self.date_night_ideas],
            "screen_time_ideas": [t.__dict__ for t in self.screen_time_ideas],
            "upcoming_deadlines": [t.__dict__ for t in self.upcoming_deadlines],
            "inbox_volume_flag": self.inbox_volume_flag,
        }


def _run_skill(skill_path: str | Path, args: list[str]) -> Any:
    """Run a bash skill, parse stdout as JSON, return parsed value.

    Raises CalledProcessError on non-zero exit. Tests should monkeypatch this.
    """
    result = subprocess.run(
        [str(skill_path)] + args,
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def compute_week_window(today: date | None = None) -> tuple[date, date, date]:
    """Return (week_start, week_end, horizon_end).

    week_start is the next Friday on/after `today` (Friday=Friday counts as start).
    week_end is week_start + 6 days (Thursday).
    horizon_end is week_end + 21 days.
    """
    if today is None:
        today = date.today()
    # Python weekday: Mon=0 ... Sun=6. Friday = 4.
    days_until_friday = (4 - today.weekday()) % 7
    week_start = today + timedelta(days=days_until_friday)
    week_end = week_start + timedelta(days=6)
    horizon_end = week_end + timedelta(days=21)
    return week_start, week_end, horizon_end


def fetch_calendar_range(
    *,
    calendar_id: str,
    start: date,
    end: date,
    source_tag: str,
    exclude_recurring: bool = False,
) -> list[Event]:
    """Fetch events from a single calendar across an inclusive date range.

    Calls the gcal-fetch skill once per day in the range, merges, tags each
    event with `source_tag`.
    """
    events: list[Event] = []
    cur = start
    while cur <= end:
        args = ["--calendar-id", calendar_id, "--date", cur.isoformat()]
        if exclude_recurring:
            args.append("--exclude-recurring")
        raw = _run_skill(GCAL_FETCH, args)
        for e in raw:
            events.append(Event(
                title=e.get("title", "(no title)"),
                date=cur.isoformat(),
                start=e.get("start", ""),
                end=e.get("end", ""),
                location=e.get("location", ""),
                source=source_tag,
            ))
        cur += timedelta(days=1)
    return events
