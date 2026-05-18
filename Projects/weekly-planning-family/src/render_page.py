"""Render session.html from Context + LLM output JSON files."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.constants import PROJECT_ROOT
from src.fetch_sources import Context, Event, Task

# Resolve templates relative to this file so it works both in-worktree and
# at the production path without needing the constants.TEMPLATES_DIR value.
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "jinja"]),
    )


def _week_days(ctx: Context) -> list[dict]:
    """Build a list of {label, iso, events[]} dicts for each day of the planning week."""
    by_date: dict[str, list[Event]] = {}
    for e in ctx.general_events + ctx.personal_events + ctx.school_events:
        by_date.setdefault(e.date, []).append(e)
    days = []
    cur = ctx.week_start
    while cur <= ctx.week_end:
        iso = cur.isoformat()
        days.append({
            "label": cur.strftime("%a %b %-d"),
            "iso": iso,
            "events": sorted(by_date.get(iso, []), key=lambda e: e.start),
        })
        cur += timedelta(days=1)
    return days


def _weekday_days(ctx: Context) -> list[dict]:
    """Mon–Fri rows for the home-schedule fieldset."""
    cur = ctx.week_start
    while cur.weekday() != 0:  # find next Monday
        cur += timedelta(days=1)
    out = []
    for i in range(5):
        d = cur + timedelta(days=i)
        out.append({"label": d.strftime("%a %b %-d"), "iso": d.isoformat()})
    return out


def _horizon_events(ctx: Context) -> list[Event]:
    """Events tagged as horizon (beyond the 7-day window)."""
    return [e for e in ctx.general_events if e.source == "general-horizon"]


def _date_night_suggestions(ctx: Context, n: int = 3) -> list[str]:
    """First N items from Screen time + first N from Date Night Ideas, interleaved."""
    out: list[str] = []
    for i in range(n):
        if i < len(ctx.date_night_ideas):
            out.append(f"Out: {ctx.date_night_ideas[i].content}")
        if i < len(ctx.screen_time_ideas):
            out.append(f"At home: {ctx.screen_time_ideas[i].content}")
    return out


def render(
    *,
    ctx: Context,
    retrospective: dict,
    margin_flags: dict,
    cfm_lesson_title: str,
) -> str:
    """Render the form HTML."""
    env = _env()
    template = env.get_template("session.html.jinja")
    return template.render(
        ctx=ctx,
        retrospective=retrospective,
        margin_flags=margin_flags,
        week_days=_week_days(ctx),
        week_days_weekday=_weekday_days(ctx),
        horizon_events=_horizon_events(ctx),
        date_night_suggestions=_date_night_suggestions(ctx),
        cfm_lesson_title=cfm_lesson_title,
        generated_at=datetime.now().strftime("%a %b %-d %-I:%M %p"),
    )


def _rehydrate_context(d: dict) -> Context:
    """Convert serialized context.json back into a Context dataclass."""
    return Context(
        week_start=date.fromisoformat(d["week_start"]),
        week_end=date.fromisoformat(d["week_end"]),
        horizon_end=date.fromisoformat(d["horizon_end"]),
        general_events=[Event(**e) for e in d["general_events"]],
        meal_events_last=[Event(**e) for e in d["meal_events_last"]],
        personal_events=[Event(**e) for e in d["personal_events"]],
        school_events=[Event(**e) for e in d["school_events"]],
        meals_library=[Task(**t) for t in d["meals_library"]],
        date_night_ideas=[Task(**t) for t in d["date_night_ideas"]],
        screen_time_ideas=[Task(**t) for t in d["screen_time_ideas"]],
        upcoming_deadlines=[Task(**t) for t in d["upcoming_deadlines"]],
        inbox_volume_flag=d["inbox_volume_flag"],
    )


def main() -> None:
    """CLI entry: read context.json + retrospective.json + margin_flags.json, write session.html."""
    with open(PROJECT_ROOT / "context.json") as f:
        ctx_dict = json.load(f)
    with open(PROJECT_ROOT / "retrospective.json") as f:
        retrospective = json.load(f)
    with open(PROJECT_ROOT / "margin_flags.json") as f:
        margin_flags = json.load(f)

    ctx = _rehydrate_context(ctx_dict)

    # CFM lesson title — placeholder; resolved in Stage 6 SKILL.md task.
    cfm_title = "this week's lesson"

    html = render(
        ctx=ctx,
        retrospective=retrospective,
        margin_flags=margin_flags,
        cfm_lesson_title=cfm_title,
    )

    out = PROJECT_ROOT / "session.html"
    with open(out, "w") as f:
        f.write(html)
    print(f"session.html written: {out}")


if __name__ == "__main__":
    main()
