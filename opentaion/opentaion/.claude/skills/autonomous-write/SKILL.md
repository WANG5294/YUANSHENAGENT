---
name: autonomous-write
description: >
  Write all remaining sections of the OpenTalon book without stopping for
  human confirmation between sections. Reads progress.md to find the first
  incomplete section, writes each section in turn using the full write-section
  procedure, and continues until every section marked ○ is marked ●.
  Resumable: if interrupted, invoke again and it continues from the first ○.
argument-hint: "[optional: ref to start from, e.g. 1.2.3 — defaults to first ○ in progress.md]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Skill: autonomous-write

You are writing the entire manuscript of *OpenTalon: Building an Agentic
Coding Assistant with Claude Code*, one section at a time, without stopping
for human confirmation. This is a sustained precision task across 110+
sections. Do not take shortcuts because no human is watching. The quality
standards in `book/style-guide.md` apply in full to every section.

---

## File Path Convention

Sections are stored at:

```
book/chapters/prologue/s{N}.md          ← for refs 0.0.1, 0.0.2, 0.0.3
book/chapters/part-{P}/ch{CC}/s{N}.md  ← for all other refs
book/chapters/epilogue/s{N}.md          ← for refs 7.0.1, 7.0.2
```

Where `{P}` is the part number (1–6), `{CC}` is the chapter number
zero-padded to two digits (01–21), and `{N}` is the section number (1–5).

Examples:
- ref `0.0.2` → `book/chapters/prologue/s2.md`
- ref `1.2.3` → `book/chapters/part-1/ch02/s3.md`
- ref `2.4.5` → `book/chapters/part-2/ch04/s5.md`
- ref `3.11.2` → `book/chapters/part-3/ch11/s2.md`
- ref `7.0.1` → `book/chapters/epilogue/s1.md`

Create the directory if it does not exist before writing the file.

---

## Before the First Section: Initialize

**Step A: Set autonomous mode active**

Edit `book/progress.md`. In the Autonomous Mode Settings block, change:
```
autonomous-mode : false
```
to:
```
autonomous-mode : true
started-at      : [today's date — 2026-03-14]
```

**Step B: Find the starting section**

Read `book/progress.md`. Scan the Full Progress Table from top to bottom.
Find the first section with status `○` (not started). That is your starting
point.

If an argument was provided to this skill (e.g. `2.4.1`), start at that ref
instead — but verify it has status `○` first. If it has status `●`, find
the next `○` from that point forward.

**Step C: One-time style orientation**

Read `book/style-guide.md` completely before writing the first section.
You will not re-read it during the run — carry it in working context for
the duration. Pay particular attention to Section 4 (forbidden words) and
Section 6 (code block standards).

---

## The Section Loop

For each section until all `○` entries are `●`, execute the following four
loop steps. Do not skip any. Complete one section fully before beginning
the next.

---

### Loop Step 1: Execute the write-section procedure

Follow Steps 1 through 7 of the `write-section` skill exactly.
Autonomous mode does not lower the quality bar.

The steps in brief (see `write-section.md` for the full procedure):

1. **Orient** — read `book/progress.md`, find the current section's entry in
   `book/outline.md`, read `book/opentaion-state.md`, read the preceding
   section file if it exists.

   **Efficiency note for outline.md (large file):** Rather than reading the
   entire outline every iteration, use Grep to find the target ref, note the
   line number, then read ~50 lines from that offset. The format is:
   ```
   grep -n "ref: {P}.{C}.{S}" book/outline.md → get line number N
   Read book/outline.md, offset: N, limit: 40
   ```

2. **Check for code requirements** — if the outline entry has a milestone,
   check opentaion-state.md for prerequisites, build and verify the code
   before writing a word of prose about it.

3. **Plan** — state the single claim, identify the OpenTalon Connection,
   decide on analogy (if needed), know the closing direction.

4. **Verify consistency** — terminology and tech stack checks.

5. **Write** — follow the section template exactly. Every section needs:
   Opening (1–2 paragraphs) · Concept (2–4 paragraphs) ·
   OpenTalon Connection (exactly 1 paragraph) · Code block (if milestone) ·
   What Just Happened (if code) · Closing (1 paragraph).
   Word count: 400–700 words conceptual, 600–1000 words with code.
   Hard ceiling: 1200 words.

6. **Self-review** — all checklist items from write-section.md Step 6 must
   pass before saving.

7. **Update state files** — update `book/progress.md` (mark `○` → `●`,
   update Last Session block, update section counts) and
   `book/opentaion-state.md` if code was written.

---

### Loop Step 2: Log decisions and ambiguities

After completing Step 7, before moving to the next section:

Review what you just wrote. For every decision the outline did not
explicitly specify — a scope judgment, a code implementation choice, a
voice deviation, a forward-reference — add one line to
`book/progress.md` under "Autonomous Decisions Log":

```
[Section P.C.S] [type] Decision made. Reasoning in one sentence.
```

Types:
- `interpretation` — scope or content judgment beyond the outline's must-cover
- `code` — implementation choice where the outline specified a milestone but
  not the implementation
- `voice` — structural or length deviation from the template
- `forward-ref` — referenced future OpenTalon state that has not been built yet
- `contradiction` — current section contradicts an earlier section; earlier
  section marked `⚑` in progress table

If you made no non-obvious decisions, do not add an entry. Do not pad the log.

---

### Loop Step 3: Compact anchor (every 20 sections)

After every 20th section completed — when the total completed count is a
multiple of 20 — append a compact anchor to `book/progress.md`:

```markdown
## Compact Anchor — After Section {P.C.S} ({N}/110 complete)

Date: {today}. {N} of 110 sections complete. Parts {X} through {Y} done.
OpenTalon milestone last reached: {milestone name or "none yet"}.
Last autonomous decision: {most recent entry from decisions log, one line}.
Next section: {P.C.S} — "{title from outline}".
On restart: read this anchor, then run /autonomous-write.
```

Keep each anchor under 100 words. This is the orientation point after any
context compaction or process interruption. Write it to disk before
continuing to the next section — it is worthless if it is only in context.

---

### Loop Step 4: Proceed to next section

Read `book/progress.md`. Find the next section with status `○` after the
one just completed. If found: return to Loop Step 1 for that section.

If no `○` sections remain in the progress table: go to Final Step.

---

## Ambiguity Policy

When the outline entry is not specific enough to write with confidence,
apply these rules in order. Do not stop the run. Do not ask for input.
Make the decision, log it, continue.

**Rule 1 — Make the decision, do not defer.**
A reasonable decision made now is better than a perfect decision never made.
The annotation pass (when you print and read the manuscript) is when you
refine. The autonomous run is when you draft.

**Rule 2 — Use must-cover as the floor, not the ceiling.**
If the outline's must-cover list is thin, fill the section with the most
relevant supporting material — concepts, examples, or OpenTalon implications
a reader would expect at this point. Do not invent milestones or code the
outline does not call for.

**Rule 3 — Forward-reference future OpenTalon state correctly.**
- *Before a milestone section*: describe what will be built using phrases
  like "In Chapter 9, when we write the agent loop..." Never write
  speculative code that has not been built and verified.
- *At a milestone section*: build and run the code before writing prose.
  The code block must show real output, not illustrative output.
- *After a milestone section*: reference `opentaion-state.md` for what
  exists. Do not re-derive it from memory.

**Rule 4 — When word count conflicts with completeness.**
Prefer content completeness. The 400–1200 word range is guidance. A 1350-word
section that covers everything is better than a 700-word section that is
thin. Log it as a `voice` decision. Never truncate to hit a target.

**Rule 5 — When the OpenTalon Connection is not obvious.**
Ask: what specific file, design decision, or constraint in OpenTalon does
this concept directly affect? If the connection is not concrete yet, use a
forward-reference: "OpenTalon confronts this problem directly in Chapter N,
when [specific scenario]." This is always valid and always honest.

**Rule 6 — When the current section contradicts an earlier section.**
Do not silently resolve it. Do both of the following:
(a) In the progress table, change the earlier section's status from `●` to `⚑`.
(b) Add a `contradiction` entry to the Autonomous Decisions Log with both
    section refs and the nature of the conflict.
Write the current section consistent with the book's overall direction.
The human reconciles during the annotation pass.

---

## Restart / Recovery

If this run was interrupted by a crash, timeout, or manual stop:

1. The human types `/autonomous-write`.
2. This skill reads `book/progress.md`.
3. If `autonomous-mode: true` is already set, skip Initialize Step A.
4. Find the first `○` section in the progress table. Continue from there.
5. If a compact anchor was written before the interruption, it appears in
   `progress.md` and provides orientation context on the re-read.

Recovery requires no human intervention beyond typing `/autonomous-write`.
No section is re-written. No state is lost.

---

## Final Step: Complete the Run

When no `○` sections remain in the progress table:

**1. Run the session-wrap procedure (all 7 steps from `session-wrap.md`).**
Pay particular attention to Step 2 (verify opentaion-state.md accuracy)
and Step 6 (sensitive data check across all newly created section files).

**2. Update the Autonomous Mode Settings block in `book/progress.md`:**
```
autonomous-mode : complete
ended-at        : [today's date]
```

**3. Update the Section Count block in `book/progress.md`:**
```
Completed              : [final count]
Remaining              : 0
```

**4. Report to the human:**

```
✓ Autonomous run complete: [date]

  Sections written   : [N] / [total from progress table]
  Milestones reached : [list each milestone reached, e.g. M1 (2.5), M2 (3.5)]
  Decisions logged   : [count of entries in Autonomous Decisions Log]
  Sections flagged ⚑ : [count, or "none"]
  Sensitive data     : none found (or: [count] items redacted — see session log)

  The manuscript draft is complete. All section files exist in
  book/chapters/. The Autonomous Decisions Log in progress.md contains
  [N] entries to review during the annotation pass.

  Suggested first step for annotation:
    1. Read book/progress.md — Autonomous Decisions Log
    2. Read book/progress.md — all ⚑ entries (contradictions to reconcile)
    3. Read from book/chapters/prologue/s1.md forward
```
