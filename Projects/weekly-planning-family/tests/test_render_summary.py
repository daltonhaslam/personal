from src.render_summary import render_summary


def test_summary_includes_decisions_and_writeback_results():
    decisions = {
        "retrospective_note": "Tough week, but we made it.",
        "dinners": [{"day": "Fri", "meal": "Tacos"}, {"day": "Sat", "meal": "Leftovers"}],
        "shopping_necessary": ["milk", "eggs"],
        "shopping_wants": ["sourdough starter kit"],
        "home_schedule": [{"day": "Mon", "note": "WFH"}, {"day": "Tue", "note": "Home by 5:00 PM"}],
        "art_blocks": [{"date": "2026-05-24", "start": "14:00", "end": "16:00"}],
        "babysitter": {"date": "2026-05-24", "time": "18:00", "who": "Sarah"},
        "kids_activities": [{"date": "2026-05-23", "time": "10:00", "title": "Soccer", "owner": "Both"}],
        "church_lines": ["Temple Friday at 10am"],
        "home_lines": ["Replace bathroom faucet"],
        "new_deadlines": ["Renew passport — June 1"],
        "finances_notes": "Need to revisit budget.",
        "cfm_notes": "Both teaching together.",
        "date_night": {"date": "2026-05-24", "time": "19:00", "choice": "Out: ramen place"},
    }
    results = {
        "succeeded": [
            {"label": "Calendar events", "detail": "Created 5 events", "key": "calendar"},
            {"label": "Todoist tasks", "detail": "Created 8 tasks across 5 projects", "key": "todoist"},
        ],
        "failed": [],
    }
    html = render_summary(
        decisions=decisions,
        results=results,
        week_start_display="May 22",
        saved_at="Thu May 21 8:45 PM",
    )
    assert "Tacos" in html
    assert "Sarah" in html
    assert "Created 5 events" in html
    assert "Soccer" in html
    assert "Both" in html
    assert "May 22" in html


def test_summary_shows_failed_block_with_retry_button():
    decisions = {
        "retrospective_note": "", "dinners": [], "shopping_necessary": [], "shopping_wants": [],
        "home_schedule": [], "art_blocks": [], "babysitter": None, "kids_activities": [],
        "church_lines": [], "home_lines": [], "new_deadlines": [],
        "finances_notes": "", "cfm_notes": "", "date_night": None,
    }
    results = {
        "succeeded": [{"label": "Calendar events", "detail": "Created 2 events", "key": "calendar"}],
        "failed": [{"label": "Todoist tasks", "error": "API timeout", "key": "todoist"}],
    }
    html = render_summary(
        decisions=decisions, results=results,
        week_start_display="May 22", saved_at="now",
    )
    assert "Failed writes" in html
    assert "API timeout" in html
    assert "retry" in html.lower()
