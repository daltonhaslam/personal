# Weekly Planning — Retrospective Prompt

You are summarizing last week for Dalton and Maggie's weekly planning session.

## Input

Read `context.json` from the project root. Relevant fields:

- `meal_events_last` — events from the meal calendar in the last 7 days
- `general_events` — events on the shared general calendar from `week_start` minus 7 to `week_end`
- `dalton_gmail`, `maggie_gmail`, `kid_school_emails` — message digests (snippet, sender, subject, date) from the last 7 days
- `upcoming_deadlines` — Todoist tasks with deadlines in the next 14 days

## Task

Produce 5-10 short bullets that capture what happened last week. Mix of:

- Notable calendar events that took place (skip routine ones)
- What got eaten (1 line summarizing the week's dinners)
- Anything in the email digests that the user likely cares about for retrospective context (e.g., school news, appointment outcomes)
- Anything that *slipped* — Todoist deadlines that passed without being completed, missed events, etc.

Bullets should be one short sentence each. No padding. No emojis. Use plain language.

## Output

Write to `retrospective.json` at project root:

```json
{
  "bullets": [
    "Soccer practice happened Mon and Wed; the Saturday game was rained out.",
    "Three home dinners (pasta, tacos, chicken) plus a Friday takeout night.",
    "Two school emails about field day on May 23rd; both parents need to RSVP.",
    "Car registration renewal deadline (May 17) passed without being done — top of this week's list."
  ]
}
```

Five to ten bullets. Strict JSON output. Do not echo anything else to stdout/stderr.
