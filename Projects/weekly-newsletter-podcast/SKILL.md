---
name: weekly-newsletter-podcast
description: Fetch weekly newsletters, generate two-host podcast script and newsletters-processed summary
---

This is an automated run of a scheduled task. The user is not present. Execute autonomously without asking questions.

You are generating a weekly newsletter podcast script for Dalton Haslam. This task runs every Monday evening. It fetches newsletters and writes a dialogue script + newsletters-processed HTML to disk. The run script handles audio synthesis after Claude completes.

## Available Tools
- Bash tool: for Gmail CLI scripts and running shell commands
- Write tool: for writing files

---

## STEP 1 — Fetch Newsletter Emails (past 7 days)
For each source, search then read full content via Bash. Run searches sequentially.

**Sources and commands:**

1. **Healthcare Brew:**
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh \
  --query "from:healthcarebrew@morningbrew.com newer_than:7d" --max-results 7
# For each id returned:
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/read-email.sh \
  --message-id <id> --depth full
```

2. **Health Tech Nerds** (weekly only — skip event invites):
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh \
  --query "from:newsletter@mail.healthtechnerds.com newer_than:7d" --max-results 3
# Include ONLY emails with "Weekly Health Tech Reads" in subject. For those:
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/read-email.sh \
  --message-id <id> --depth full
```

3. **Book Freak:**
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh \
  --query "from:no-reply@substack.com subject:\"Book Freak\" newer_than:7d" --max-results 3
# For each id returned:
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/read-email.sh \
  --message-id <id> --depth full
```

4. **ACPA News to Note:**
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh \
  --query "from:info@acpadvisors.org subject:\"News to Note\" newer_than:7d" --max-results 3
# For each id returned:
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/read-email.sh \
  --message-id <id> --depth full
```

5. **Robert Oubre MD:**
```bash
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/search-emails.sh \
  --query "from:dr_oubre@robertoubremd.com newer_than:7d" --max-results 3
# For each id returned:
bash /Users/daltonhaslam/Documents/Claude/Personal/skills/gmail-fetch/read-email.sh \
  --message-id <id> --depth full
```

If no newsletters found at all, write a podcast_error.html to /Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/podcast_error.html explaining no content was found, then stop.

---

## STEP 2 — Generate Podcast Script

Write a two-host podcast script from the newsletter content.

**Target length:** 18–22 minutes of spoken audio. At natural conversational pace (~130 words/minute), this is approximately 2,400–2,900 words of dialogue. Write enough to hit this target — don't pad, but don't stop short.

**Hosts:**
- Host A: more explanatory and structured
- Host B: more curious and reactive, occasional light humor

**Structure:**
1. Hook (1–2 min): Open with the most interesting idea — grab attention immediately
2. Main segments: One per newsletter source (or merged if topics overlap). Natural conversation. Host A introduces each source naturally: "So this week's Healthcare Brew had something interesting about..."
   - When a source had multiple emails, synthesize the best highlights across all of them into one unified segment — do not cover each email individually. Airtime per source should reflect content significance and novelty, not email count. A source with 5 thin emails does not outweigh a source with 1 deeply analytical one.
   - Allocate time proportionally to content depth: a source with 4+ substantive topics warrants 4–6 minutes; a source with 1–2 items warrants 1–2 minutes.
3. Key Takeaways (1–2 min): 3–5 most important or actionable ideas
4. Close (30 sec): Brief natural sign-off

**Style:**
- Conversational, intelligent, never robotic
- No bullet points in dialogue
- Natural reactions: "That's wild," "Wait, so what does that mean for..."
- No monologue longer than 4–5 sentences before the other host responds
- Cover everything substantively — don't pad, don't truncate
- For each topic, go beyond summary — explain context, implications, and why it matters practically. Answer "so what?" not just "what."

**Output format — label each line exactly:**
```
Host A: [text]
Host B: [text]
```
No stage directions, no headers, no bullet points in the dialogue.

---

## STEP 3 — Write Podcast Script

```bash
python3 << 'PYEOF'
script = """PODCAST_SCRIPT_HERE"""

with open('/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/podcast_script.txt', 'w') as f:
    f.write(script)
print("Script written.")
PYEOF
```

Replace PODCAST_SCRIPT_HERE with the actual script content, properly escaped (use repr() or triple-quote carefully to avoid breaking the heredoc).

---

## STEP 4 — Write Newsletters Processed HTML

```bash
python3 << 'PYEOF'
html = """HTML_CONTENT_HERE"""

with open('/Users/daltonhaslam/Documents/Claude/Personal/Projects/weekly-newsletter-podcast/newsletters_processed.html', 'w') as f:
    f.write(html)
print("newsletters_processed.html written.")
PYEOF
```

**HTML format:**
```html
<!DOCTYPE html><html><body>
<h2>Newsletters Processed — [Date]</h2>
<p>Included in this week's podcast. Search Gmail by sender to find and delete.</p>
<h3>Healthcare Brew</h3><ul><li>[subject] — [date]</li></ul>
<h3>Health Tech Nerds</h3><ul><li>[subject] — [date] (or "None this week")</li></ul>
<h3>Book Freak</h3><ul><li>[subject] — [date] (or "None this week")</li></ul>
<h3>ACPA News to Note</h3><ul><li>[subject] — [date] (or "None this week")</li></ul>
<h3>Robert Oubre MD</h3><ul><li>[subject] — [date] (or "None this week")</li></ul>
<hr><p><i>Podcast: podcast_[YYYYMMDD].mp3 — iCloud Drive → Claude-Audio. Generated using Lee + Ava neural voices.</i></p>
</body></html>
```

---

## Rules
- NEVER send any email. Read-only.
- No patient data.
- If a source has no emails that week, skip that segment gracefully in the script.
- Always write podcast_script.txt — the run script handles audio synthesis after Claude completes.
