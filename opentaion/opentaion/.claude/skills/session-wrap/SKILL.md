---
name: session-wrap
description: >
  Run before ending any Claude Code session. Captures decisions, discoveries,
  and open questions made during the conversation that are not yet persisted
  to files. Updates all state files. Produces a session summary so the next
  session starts with full context. This skill is the difference between
  sessions that build on each other and sessions that repeat themselves.
argument-hint: "[optional: any specific things to make sure are captured]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
---

# Skill: session-wrap

Run this skill before closing Claude Code. It takes 2–4 minutes and saves
30–60 minutes of context reconstruction at the start of the next session.

---

## Step 1: Harvest the Conversation

Read the full conversation history of this session. Extract everything that
is not yet persisted to a file. Specifically look for:

**Decisions made:**
- Any architecture or design decisions discussed but not written to architecture.md or SPEC.md
- Any changes to the tech stack or tooling (even tentative ones)
- Any deviations from the original outline or CLAUDE.md rules that were agreed to
- Any "we'll handle that in a future section" commitments

**Discoveries:**
- Any bugs or unexpected behaviors found during this session
- Any tool, library, or pattern that worked better than expected
- Any tool, library, or pattern that was tried and abandoned — and why
- Any Claude Code behavior observed that should inform future sessions

**Open questions:**
- Anything that came up but was not resolved
- Any decision that was deferred
- Any "I'm not sure about this" moments that need follow-up

**Code state:**
- Any files created or modified outside the write-section skill's normal flow
- Any commands run that changed the opentaion/ repository structure
- Any environment variables set or external services configured

---

## Step 2: Check State File Accuracy

Read `book/opentaion-state.md` and verify it reflects the actual current
state of the opentaion/ repository.

```bash
# Confirm what actually exists vs what opentaion-state.md claims
find opentaion/ -type f -name "*.py" -o -name "*.ts" -o -name "*.tsx" | sort
```

For any file that exists but is marked `[TARGET]` in opentaion-state.md:
- Update the marker to `[EXISTS]`
- Add it to the appropriate "Files that exist" list in its component section

For any implementation that was completed during this session:
- Add the functions or endpoints to the "implemented" lists
- Note any known issues or rough edges discovered

---

## Step 3: Check Progress File Accuracy

Read `book/progress.md`. Verify:

- The Last Session block reflects what actually happened today (not what was
  planned — what was done)
- Every section completed today has status `●` in the progress table
- Any section started but not finished has status `◑`
- Any section flagged for revision has status `⚑`
- The section counts at the bottom are correct

Update anything that is stale or incorrect.

---

## Step 4: Capture Decisions and Discoveries

If decisions, discoveries, or open questions were found in Step 1:

Append them to `book/progress.md` under a new section:

```markdown
## Session Log: [today's date]

### Decisions Made
- [each decision, one line, with enough context to understand it cold]

### Discoveries
- [each discovery, one line, with the implication for future work]

### Open Questions
- [each open question, one line, tagged with the section it relates to if known]

### Deferred Items
- [anything explicitly deferred, with a note of when/where it should be resolved]
```

If there is nothing to capture — no decisions, no discoveries, no questions —
write "Session Log: [date] — nothing to capture beyond skill-managed updates."
Do not omit the log entry. Its absence would be ambiguous.

---

## Step 5: Write the Re-Entry Prompt

This is the most valuable output of this skill. Write a single paragraph —
80 to 120 words — that the next Claude Code session can use as its opening
orientation.

The re-entry prompt answers: "What was happening, what was decided, and
what is the exact next action?"

Format:
```markdown
## Re-Entry Prompt: [today's date]

[The paragraph. Present tense. No lists. Written as if briefing a colleague
who has been away for 24 hours. End with the exact command or task that
should come first in the next session.]
```

Append this to the Last Session block in `book/progress.md`.

**Good re-entry prompt example:**
> We finished Section 2.4.3 (Monorepo CLAUDE.md Strategy) and started
> scoping Section 2.4.4. The decision was made to cut the CLAUDE.md
> anti-patterns discussion into its own section (2.4.5) because 2.4.4
> was running long. The cli/CLAUDE.md file was created but is only
> partially filled in — it needs the uv-specific commands added.
> The `opentaion/cli/CLAUDE.md` file currently has a placeholder
> comment where the build commands should go. Start next session with:
> `/write-section 2.4.4` after filling in the cli/CLAUDE.md placeholder.

**Bad re-entry prompt example:**
> We worked on CLAUDE.md stuff and made some decisions. There are some
> things to do next time. Good progress was made overall.

The good example is specific enough that Claude Code can orient in 30 seconds.
The bad example requires re-reading the entire session history.

---

## Step 6: Verify No Sensitive Data in Files

```bash
# Check that no API keys or tokens were accidentally written to tracked files
grep -r "sk-" book/ opentaion/ --include="*.md" --include="*.py" \
     --include="*.ts" --include="*.tsx" 2>/dev/null | grep -v ".env.example"

grep -r "Bearer " book/ opentaion/ --include="*.md" 2>/dev/null
```

If any results appear: identify the file, remove the sensitive value,
replace it with a placeholder like `[REDACTED - use environment variable]`,
and note it in the session log.

---

## Step 7: Final Confirmation

Report to the user:

```
✓ Session wrap complete: [today's date]

  State files updated  : [list any that were changed]
  Sections completed   : [count for this session]
  Sections total       : [●]/112
  Decisions captured   : [count, or "none"]
  Open questions       : [count, or "none"]
  Sensitive data found : [count, or "none"]

  Re-entry prompt written to progress.md.

  To resume next session:
    claude --continue         ← if resuming within 24 hours (same session context)
    claude                    ← if starting fresh (reads progress.md for context)

  First command next session:
    [exact command from re-entry prompt]
```

Then stop. The session is wrapped.
