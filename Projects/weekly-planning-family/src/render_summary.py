"""Render the post-save summary HTML (page swap + archive)."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "jinja"]),
    )


def render_summary(
    *,
    decisions: dict,
    results: dict,
    week_start_display: str,
    saved_at: str,
) -> str:
    """Render the summary HTML.

    `decisions` is the structured form output (see write_back.parse_form).
    `results` has shape {"succeeded": [{label, detail, key}], "failed": [{label, error, key}]}.
    """
    env = _env()
    template = env.get_template("summary.html.jinja")
    return template.render(
        decisions=decisions,
        results=results,
        week_start_display=week_start_display,
        saved_at=saved_at,
    )
