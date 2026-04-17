# What Now? Widget — Design Notes

**Status:** Future / Unbuilt (Phase 3)
**Created:** 2026-04-14

## Vision
An iOS Shortcut on the iPhone home screen / widget. When tapped, calls Claude with real-time context and returns a task recommendation in seconds — answering "What should I work on right now?"

## Context Claude Gets
- Current time + day of week
- Location (home / work / commute — detected via Shortcuts location block)
- Todoist tasks: due dates, priorities, projects
- Today's remaining calendar events (Google Calendar MCP)
- User-provided inputs: "I have 20 minutes" / "I'm tired" / "I need something low-effort"

## Output Format
1–3 specific task recommendations with brief reasoning. Example:
> "You have 25 min before your 3pm call and you're at your desk. Best use: finish the CDI query backlog review (due today, 20 min estimate). If you need something lighter, reply to the school email about Thursday's schedule."

## Build Path
iOS Shortcut → Claude API (claude-sonnet-4-6) → response displayed in notification or Shortcuts result screen.

## Open Questions
- Location detection: GPS coordinates vs. named places via Shortcuts location block
- Task deduplication: if email creates a Todoist task that Dalton also manually adds, avoid double-recommendation

## Notes from Phase 1
- Gmail MCP is read-only; iMessage is out of scope
- Work email cannot be connected (no MCP available for MWHC system)
- HIPAA: no patient data flows through this system
- Shared Todoist: wife's tasks should not appear in recommendations
