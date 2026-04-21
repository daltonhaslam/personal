# Apple Shortcuts Setup — Communication OS

These Shortcuts run automatically on the Mac and pick up output files written by the scheduled Claude tasks.

---

## ~~Shortcut 1: Daily Brief → Apple Notes~~ (Retired)

The daily brief now creates the Apple Note directly via `run_daily_brief.sh` using osascript. No Shortcut required. If this Shortcut still exists in Shortcuts.app it can be deleted or disabled.

---

## Shortcut 2: Newsletters Processed → Apple Notes

**Actions:**
1. Get File → `~/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/newsletters_processed.html`
2. Create Note with (File) in iCloud Notes — Name: `Newsletters Processed`

**Automation:** Every Monday at 7:15 PM, Run Immediately

---

## Shortcut 3: Monthly Maintenance → Apple Notes

**Actions:**
1. Get File → `~/Documents/Claude/Personal/Projects/monthly-comms-maintenance/maintenance.html`
2. Create Note with (File) in iCloud Notes — Name: `Comm OS Maintenance`

**Automation:** Monthly on the 1st at 7:15 PM, Run Immediately

---

## Shortcut 4: Todoist Failure Monitor

**Actions:** Watches for file existence, then creates Apple Note alert

**File path:** `~/Documents/Claude/Personal/Projects/email-to-todoist-tasks/todoistfailure/todoist_failure.txt`

**Automation:** Triggered when file appears (file-based automation)

---

## File Paths Summary

| File | Written by | Read by |
|---|---|---|
| `~/Documents/Claude/Personal/Projects/daily-brief/brief.html` | daily-brief task (7:00 PM nightly) | osascript in run_daily_brief.sh (same run) |
| `~/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/newsletters_processed.html` | podcast task (Monday 7:00 PM) | Newsletters Processed Shortcut (Monday 7:15 PM) |
| `~/Documents/Claude/Personal/Projects/monthly-comms-maintenance/maintenance.html` | maintenance task (1st of month 7:00 PM) | Monthly Maintenance Shortcut (1st at 7:15 PM) |
| `~/Documents/Claude/Personal/Projects/email-to-todoist-tasks/todoistfailure/todoist_failure.txt` | email-to-todoist task (on failure) | Todoist Failure Monitor Shortcut |
| `~/Library/Mobile Documents/com~apple~CloudDocs/Claude-Audio/podcast_YYYYMMDD.mp3` | podcast task (Monday 7:00 PM) | VLC on iPhone from iCloud Drive |
