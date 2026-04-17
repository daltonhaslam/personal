# Communication OS — Project Framework

**Owner:** Dalton Haslam  
**Created:** 2026-04-14  
**Status:** Planning / Phase 0  
**Goal:** Build a unified personal communication system that captures all incoming information, intelligently categorizes it, and delivers it back in the right format at the right time — reducing cognitive load and improving intentional action.

---

## Vision

A personal operating system for information flow. Instead of being reactive to a constant stream of email, messages, and notifications, Dalton has a system that:
- Captures everything automatically
- Sorts it so nothing important gets missed and noise is filtered out
- Delivers structured, actionable briefs on a schedule
- Answers "what should I work on right now?" with real intelligence

---

## System Architecture: Three Layers

### Layer 1 — Capture (Pull It All In)
Connects to all incoming information sources. Raw data in.

| Source | Tool | Integration Path | Priority |
|---|---|---|---|
| Gmail (personal) | Gmail | Gmail MCP | Phase 1 |
| Google Calendar | Calendar | Google Calendar MCP | Phase 1 |
| Apple Calendar | Calendar | Apple Calendar (local read via Shortcuts) | Phase 1 |
| Todoist | Tasks | Todoist MCP | Phase 1 |
| Work email | Email | **Not connectable** — manual only | — |

### Layer 2 — Process (Sort and Categorize)
Claude reads everything captured and assigns it to a bucket. This is where the intelligence lives.

---

## System Rules

- **Email:** Claude may draft emails but will NEVER send. Dalton is always the final sender.
- **iMessage:** Not included in this system. Out of scope.
- **Work email:** Cannot be connected. Excluded entirely.
- **HIPAA:** No patient data ever enters this system.

### Layer 3 — Surface (Deliver Back to You)
Outputs: Daily Brief (Apple Notes), Weekly Newsletter Audio, On-Demand "What Now?" widget.

---

## Communication Buckets

Every piece of incoming communication is assigned to one of these:

| Bucket | Description | Examples |
|---|---|---|
| **Action Required** | Something needs a response or decision | Invoice approval, RSVP, doctor callback |
| **Task** | A discrete to-do → auto-imported to Todoist | "Can you send me that document?" School form due |
| **Calendar / Event** | Something time-bound to add or track | Party invite, appointment confirmation, schedule change |
| **Family** | Communication relevant to household/family coordination | Kids' school updates, wife messages, activity logistics |
| **Church** | Ward communication, Young Men activities, callings | Bishop announcements, activity reminders, ministering |
| **Newsletter / Digest** | Recurring email content for consumption, not action | Morning Brew, Axios, Substack, MedPage Today |
| **Financial** | Bills, statements, transactions | Utility bill, credit card statement, Amazon order |
| **Informational / FYI** | Low-priority, no action needed | Sale emails, app updates, general announcements |
| **Junk / Skip** | Ignore entirely | Spam, marketing with no value |

---

## Delivery Formats

### 1. Daily Brief (7pm — Apple Notes)
Runs automatically at 7pm every night. Creates/overwrites a note titled **"Daily Brief"** in Apple Notes.

**Contents:**
- Tomorrow's calendar (Google Calendar)
- Top 3–5 tasks for tomorrow (pulled from Todoist, priority + due date aware)
- Action Required items from today's email not yet handled
- Family coordination items (school pickups, activities, etc.)
- Church items if relevant

**Format:** Scannable, short. Designed to be reviewed around 8pm to plan the next day.

### 2. Weekly Newsletter Podcast (Monday 8pm — Audio)
Runs Monday evenings. Ready to listen Tuesday morning commute. Aggregates newsletters from the past 7 days.

**Confirmed newsletter sources:**

| Newsletter | Sender | Frequency | Notes |
|---|---|---|---|
| Healthcare Brew | healthcarebrew@morningbrew.com | Mon/Wed/Fri | Healthcare industry news |
| Health Tech Nerds | newsletter@mail.healthtechnerds.com | Weekly + events | Use "Weekly Health Tech Reads" issues only; skip event invites |
| Book Freak (Substack) | no-reply@substack.com | Weekly | Books/ideas; filter by "Book Freak" in subject |
| ACPA News to Note | info@acpadvisors.org | Monthly | Filter by "News to Note" in subject only |
| Robert Oubre, MD | dr_oubre@robertoubremd.com | Irregular | Include if received; went quiet as of Dec 2025 |

**Format:** Two-host podcast dialogue script → two-voice MP3 (edge-tts, free) → concatenated via ffmpeg → saved to iCloud Drive.  
**Audio folder:** `/Users/daltonhaslam/Library/Mobile Documents/com~apple~CloudDocs/Claude-Audio/`  
**File naming:** `podcast_YYYYMMDD.mp3` — previous week's file deleted automatically before saving new one.  
**Target length:** Cover everything substantively (typically 15–25 min at 1x).  
**Playback:** VLC for iOS (free) — supports variable speed from iCloud Drive.  
**TTS voices:** Host A = `en-US-GuyNeural`, Host B = `en-US-JennyNeural`.

**Script format (two-host dialogue):**
- Host A: more explanatory/structured
- Host B: more curious/reactive, asks questions
- Natural reactions, light humor, no long monologues
- Structure: Hook → topic segments by newsletter → key takeaways → close
- If topics overlap across newsletters, synthesize them

**Post-processing:** After each run, task creates an Apple Note called "Newsletters Processed" listing that week's summarized emails (sender + subject) so Dalton can batch-delete from Gmail.

**Gmail label setup (one-time manual):** Set up Gmail filters to auto-apply label "Newsletters" to all emails from the above senders. Enables bulk-delete after listening and simplifies future task search queries.

### 3. On-Demand: "What Should I Work On Now?"
A Shortcut on iPhone home screen / widget. When tapped, calls Claude with context and returns a recommendation within seconds.

**Context Claude gets:**
- Current time + day of week
- Location (home / work / commute — detected via Shortcuts)
- Todoist tasks: due dates, priorities, projects
- Today's remaining calendar events
- User-provided inputs: "I have 20 minutes" / "I'm tired" / "I need something low-effort"

**Output:** 1–3 specific task recommendations with brief reasoning. e.g.:
> "You have 25 min before your 3pm call and you're at your desk. Best use: finish the CDI query backlog review (due today, 20 min estimate). If you need something lighter, reply to the school email about Thursday's schedule."

**Build path:** iOS Shortcut → Claude API (claude-sonnet-4-6) → response displayed in notification or Shortcuts result screen.

---

## Build Phases

### Phase 1 — Core Foundation (Gmail + Calendar + Todoist)
*Goal: Get daily brief working and task extraction from email.*

- [ ] Connect Gmail via MCP
- [ ] Connect Google Calendar via MCP
- [ ] Connect Todoist via MCP
- [ ] Define newsletter sender list (email addresses to watch)
- [ ] Build daily brief generator → writes to Apple Notes
- [ ] Build email → Todoist task extractor (Claude identifies actionable emails and creates tasks)
- [ ] Test and calibrate categorization buckets

### Phase 2 — Newsletter Audio
*Goal: Weekly newsletter audio summary for Monday commute.*

- [ ] Build weekly newsletter aggregator (filter by known sender list)
- [ ] Build summarizer prompt (per-newsletter + combined)
- [ ] Select and integrate TTS service
- [ ] Establish delivery mechanism (Files app, Shortcuts, or email to self)
- [ ] Test audio quality and length

### Phase 3 — "What Now?" Widget
*Goal: Intelligent on-demand task recommendation.*

- [ ] Build iOS Shortcut with context gathering (time, location, available time input)
- [ ] Build Claude prompt with Todoist + Calendar context
- [ ] Test recommendation quality
- [ ] Refine prompt with real usage data

### Phase 4 — Refinement
*Goal: Ongoing tuning based on real use.*

- [ ] Calibrate bucket assignments (false positives, missed items)
- [ ] Tune daily brief length and format
- [ ] Add or adjust buckets as patterns emerge
- [ ] Explore Apple Watch delivery options

---

## Key Constraints & Notes

- **Work email excluded** — cannot be connected; anything from work stays manual
- **HIPAA** — no patient data ever flows through this system
- **Shared Todoist** — wife has her own account; shared lists should be respected but her tasks are not Dalton's responsibility to manage via this system
- **Apple ecosystem** — all automation should prefer native Apple tools (Shortcuts, Notes, Calendar) where possible; reduces friction and works offline
- **Iterative** — this system will not be perfect on day one; calibration over weeks 1–4 is expected and normal

---

## Open Questions

1. ~~TTS service~~ — **Resolved:** edge-tts (Microsoft neural voices, free)
2. ~~Daily brief delivery time~~ — **Resolved:** 7pm generation, reviewed ~8pm
3. ~~Newsletter identification~~ — **Resolved:** sender list confirmed (see above)
4. ~~Apple Notes write-back~~ — **Resolved:** osascript via Bash in scheduled task
5. **"What Now?" location detection** — GPS coordinates vs. named places via Shortcuts location block (Phase 3)
6. **Task deduplication** — if an email creates a task in Todoist and Dalton also manually adds it, need logic to avoid duplicates (Phase 1 calibration)
7. **Gmail labeling** — Gmail MCP is read-only; set up manual Gmail filters to auto-label newsletter senders on arrival; task generates "Newsletters Processed" Apple Note for manual bulk-delete
8. **Robert Oubre newsletter** — went quiet Dec 2025; confirm if still subscribed

---

## MCP Connectors Needed

| Connector | Status | Notes |
|---|---|---|
| Gmail | To install | Core — Phase 1 |
| Google Calendar | To install | Core — Phase 1 |
| Todoist | To install | Core — Phase 1 |
| Apple Notes write | Native / Shortcuts | No MCP needed; write via Shortcuts or file |
| iMessage | No MCP available | Phase 3 — Shortcuts workaround |

---

## Iteration Log

| Date | Change | Notes |
|---|---|---|
| 2026-04-14 | Framework created | Initial planning session |
