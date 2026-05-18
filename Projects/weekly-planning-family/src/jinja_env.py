"""Shared Jinja environment for render_page + render_summary."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

# Resolved relative to this file so rendering works regardless of cwd or whether
# the project is running in-worktree or at its production path.
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def make_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "jinja"]),
    )
