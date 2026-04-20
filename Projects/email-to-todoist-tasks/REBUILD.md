# email-to-todoist-tasks — Rebuild Plan

**Status:** Needs work — address after MCP → CLI conversions are complete (Conversions 3+)

## What Needs To Be Done

### 1. RemoteTrigger Setup
The RemoteTrigger for this task does not exist yet (only a "test-probe" is in the account). Needs to be created via `/schedule` skill before it will run automatically.

### 2. End-to-End Verification
After Conversion 2 (Gmail CLI) was completed, the email-to-todoist trigger didn't exist to test against. Need to verify:
- Gmail `search-emails.sh` works correctly within this skill's context
- Todoist `find-tasks.sh` dedup check works
- `add-task.sh` creates tasks correctly
- Step 6 (success/failure notification file) writes/deletes correctly

### 3. Other Changes Needed
(Fill in when returning to this task — note any changes to task logic, schedule, or behavior you want to make)

## How To Resume
Open this file in a new session and say: "Let's work on the email-to-todoist-tasks rebuild plan."
