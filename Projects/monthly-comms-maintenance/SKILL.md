---
name: monthly-comms-maintenance
description: Monthly check of Communication OS health — newsletter labels, new senders, and system status
---

You are running a monthly maintenance check on Dalton Haslam's Communication OS system. This task runs on the 1st of each month at 7pm. Your job is to audit the system and surface anything that needs attention — especially newsletter labeling gaps, new newsletter sources, and anything that may have drifted.

Output is an HTML file written to ~/Documents/Claude/Personal/Projects/monthly-comms-maintenance/maintenance.html. A Shortcut automation picks it up at 9:15am and creates an Apple Note titled "Comm OS Maintenance".

## Available Tools
- Gmail MCP: gmail_search_messages, gmail_read_message
- Bash tool: for writing files

---

## KNOWN NEWSLETTER SENDERS
These senders should always have the Gmail label "Newsletters" applied:

- healthcarebrew@morningbrew.com (Healthcare Brew)
- newsletter@mail.healthtechnerds.com (Health Tech Nerds)
- no-reply@substack.com with "Book Freak" in subject (Book Freak)
- info@acpadvisors.org with "News to Note" in subject (ACPA)
- dr_oubre@robertoubremd.com (Robert Oubre, MD)

---

## STEP 1 — Check for Unlabeled Newsletter Emails
For each known sender, search for emails from the past 30 days NOT labeled "Newsletters":
- `from:healthcarebrew@morningbrew.com newer_than:30d -label:Newsletters`
- `from:newsletter@mail.healthtechnerds.com newer_than:30d -label:Newsletters`
- `from:no-reply@substack.com subject:"Book Freak" newer_than:30d -label:Newsletters`
- `from:info@acpadvisors.org subject:"News to Note" newer_than:30d -label:Newsletters`
- `from:dr_oubre@robertoubremd.com newer_than:30d -label:Newsletters`

Record: sender, count of unlabeled emails, example subject lines.

---

## STEP 2 — Check for Inactive Newsletters
For each known sender, check if they've sent anything in the past 45 days. If nothing found, flag as possibly inactive.

---

## STEP 3 — Hunt for New Newsletter Candidates
Search for recurring newsletter-like emails from unknown senders:
`unsubscribe newer_than:30d -label:Newsletters -from:healthcarebrew@morningbrew.com -from:newsletter@mail.healthtechnerds.com -from:no-reply@substack.com -from:info@acpadvisors.org -from:dr_oubre@robertoubremd.com -category:promotions`

Read a sample (up to 10) and assess whether any look like recurring newsletters worth adding to the podcast. Group by sender.

---

## STEP 4 — Write the Maintenance Report File
Build the HTML report and write it to the project folder using this Bash snippet, replacing HTML_CONTENT_HERE with the full report:

```bash
python3 << 'PYEOF'
import glob, os

matches = glob.glob('/sessions/*/mnt/Claude')
workspace = matches[0] if matches else '/Users/daltonhaslam/Documents/Claude'

brief_dir = os.path.join(workspace, 'Personal/Projects/monthly-comms-maintenance')
os.makedirs(brief_dir, exist_ok=True)

html = """HTML_CONTENT_HERE"""

with open(os.path.join(brief_dir, 'maintenance.html'), 'w') as f:
    f.write(html)
print("Maintenance report written.")
PYEOF
```

**HTML format:**
```html
<h2>Comm OS — Monthly Maintenance — [Month Year]</h2>
<p><i>Generated [date] · Review and take action on any flagged items below.</i></p>
<hr>

<h3>🏷️ Unlabeled Newsletter Emails</h3>
[If none: "All known senders are correctly labeled. No action needed."]
[If found: list sender, count, example subjects, and fix instruction: "Go to Gmail Settings → Filters → confirm the filter for [sender] has Apply label: Newsletters checked."]

<h3>💤 Possibly Inactive Newsletters</h3>
[List any senders with no emails in 45 days, or "None — all sources active."]

<h3>🆕 New Newsletter Candidates</h3>
[List any new recurring senders worth considering, with brief description.]
[If none: "No new newsletter candidates detected."]
[Note: "To add a new source, open Cowork and say: Add [sender] to the newsletter podcast task."]

<h3>✅ System Status</h3>
<ul>
  <li>Daily Brief: scheduled 7pm nightly</li>
  <li>Newsletter Podcast: scheduled Monday 8pm</li>
  <li>Monthly Maintenance: scheduled 1st of each month 7pm</li>
</ul>

<hr>
<p><i>Next maintenance check: [first of next month]</i></p>
```

---

## Rules
- NEVER send any email.
- Read and report only — do not modify any emails or labels.
- Be concise — Dalton needs to scan this in under 2 minutes.
- If everything looks healthy, say so clearly.
