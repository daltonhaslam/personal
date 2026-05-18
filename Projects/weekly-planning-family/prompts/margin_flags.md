# Weekly Planning — Margin & Realism Flags Prompt

You are flagging risk areas in the upcoming week for Dalton and Maggie.

## Input

Read `context.json` from the project root. Relevant fields:

- `week_start`, `week_end` — the 7-day planning window (Fri–Thu)
- `general_events` — events on the shared general calendar within the window AND the 21-day horizon beyond
- `personal_events` — Dalton's personal calendar
- `school_events` — events from subscribed school calendars within the window
- `kid_school_emails` — recent emails tagged "Kid's School" (could surface new activities not yet on calendar)
- `upcoming_deadlines` — Todoist deadline tasks in the next 14 days
- `inbox_volume_flag` — true if any inbox hit the 50-message cap

## Task

Produce **0-5** short flags about the upcoming week. Flags are warnings to discuss during the session. Examples of valid flags:

- "Tuesday has 3 evening events — likely overcommitted."
- "No free evening this week."
- "Kid pickup Wednesday conflicts with the 3pm parent-teacher conference on shared cal."
- "Two Todoist deadlines this week (Renew car registration, File quarterly taxes) — make sure both are owned."
- "Brightwheel mentions a snack day next Tuesday that's not on the shared calendar yet."
- "High inbox volume this week — skim your inbox manually before proceeding." (only if `inbox_volume_flag` is true)

**Constraints:**
- Only flag things you can see in `context.json`. Do NOT speculate about fields the user will fill in during the session (no flags about Maggie's art time, WFH days, dinners, etc. — those are decided live).
- Each flag is one short sentence. No padding, no advice ("you should...") — just the observation.
- Return 0 flags if nothing's worth flagging. Don't pad to hit a minimum.

## Output

Write to `margin_flags.json` at project root:

```json
{
  "flags": [
    "Tuesday has 3 evening events on the shared calendar — likely overcommitted.",
    "High inbox volume this week — skim your inbox manually before proceeding."
  ]
}
```

Strict JSON. Empty list is valid (`{"flags": []}`). Do not echo anything else to stdout/stderr.
