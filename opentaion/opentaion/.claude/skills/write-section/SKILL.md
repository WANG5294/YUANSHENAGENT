---
name: write-section
description: >
  Write one section of the OpenTalon book. Reads all context files before
  writing, enforces the section template, verifies any code examples, and
  updates progress tracking after completion. Use this for every section
  without exception. Never write a section without invoking this skill.
argument-hint: "<part>.<chapter>.<section> e.g. 1.2.3 for Part 1, Chapter 2, Section 3"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Skill: write-section

You are writing one section of the book *OpenTalon: Building an Agentic
Coding Assistant with Claude Code*. This is not a chat task. This is
precision craftwork. Follow every step in order. Do not skip steps.
Do not combine steps. Do not start writing prose until Step 5.

---

## Step 1: Orient (read before anything else)

Read these files in this order. Do not proceed until all four are loaded:

1. `book/progress.md`
   — Find the "Last Session" block. Know exactly where the book stopped.
   — Find the target section in the progress table. Confirm its status is `○`.
   — If status is `●` (complete), STOP. Tell the user this section is already
     done and ask which section to write next.

2. `book/outline.md`
   — Find the entry for the target section.
   — Read the title, milestone (if any), and any notes.
   — Understand what this section must accomplish before writing a word.

3. `book/opentaion-state.md`
   — Read the Current Version block and Component Status sections.
   — Note which files `[EXIST]` and which are `[TARGET]`.
   — This is your constraint: you may only reference code that exists.
     If a section requires code that doesn't exist yet, you build it
     before writing the prose that describes it.

4. `book/style-guide.md`
   — Skim Section 4 (forbidden words) and Section 6 (code block standards).
   — These are your hardest constraints.

Then read the immediately preceding section file (if it exists). Find it by
checking progress.md for the last completed section, then reading that file.
Your section must feel like it follows naturally from that one.

---

## Step 2: Check for Code Requirements

Look at the outline entry for this section. Does it have a milestone?

**If YES — this section introduces working code:**

  a. Check `opentaion-state.md` to confirm prerequisite files exist.
     If prerequisites are missing, create them now using the tech stack
     from `CLAUDE.md` Section 4. Use `uv` for Python, Vite for web.

  b. Write the code first. Create the actual file in the opentaion/
     repository. Use the exact file path from the repository structure
     in `opentaion-state.md`.

  c. Run the code to verify it works:
     ```bash
     # For CLI code:
     cd opentaion/cli && uv run python -m opentaion "test prompt"

     # For API code:
     cd opentaion/api && uv run uvicorn opentaion_api.main:app --reload

     # For web code:
     cd opentaion/web && npm run dev
     ```

  d. If the code fails, fix it before writing prose. Never write
     "run this and you'll see..." around code that doesn't work.

  e. Note the exact output you observed. You will use it as the
     "Expected output" in the code block.

**If NO — this section is conceptual:**

  Proceed to Step 3. No code to verify.

---

## Step 3: Plan the Section (think before writing)

Before opening an editor, answer these questions internally:

1. **What is the single claim this section makes?**
   Write it as one sentence. This becomes the opening sentence of the section.
   If you cannot state it in one sentence, the section is trying to do too much.

2. **What is the OpenTalon Connection?**
   How does this concept apply directly to what we are building?
   If you cannot answer this, re-read the outline entry. The connection
   must be concrete — not "this is important for OpenTalon" but
   "in OpenTalon's context manager, this means X."

3. **What analogy (if any) makes the concept accessible?**
   Use an analogy only if the concept is genuinely abstract. Do not
   force one. A bad analogy is worse than no analogy.

4. **What does the closing sentence point toward?**
   The last paragraph must create momentum toward the next section.
   Know where you are going before you write where you are.

---

## Step 4: Verify Consistency

Run these checks before writing:

**Terminology check:**
```bash
# Confirm spelling of key terms in existing sections
grep -r "OpenTalon\|Claude Code\|BMAD\|OpenRouter" book/chapters/ | head -20
```
Use whatever capitalization and spacing the existing sections use.

**Tech stack check:**
```bash
# Confirm no drift from agreed stack
grep -r "Next\.js\|Express\|Django\|MongoDB\|Prisma" book/chapters/
```
If any results appear, that is a consistency error in a previous section.
Flag it in `progress.md` with the `⚑` marker. Do not silently use the
wrong technology in the new section.

**Previous section ending:**
Read the last paragraph of the preceding section. Your opening sentence
should feel like a natural continuation. It does not need to reference
the previous section explicitly — but the reader should not feel a jolt.

---

## Step 5: Write the Section

Create the file at: `book/chapters/part-{N}/ch{NN}/s{N}.md`

Example: Section 2.3 goes in `book/chapters/part-1/ch02/s3.md`

Follow this template exactly. Every element is required.
Do not add elements. Do not remove elements.

```markdown
## Section {X.Y}: {Title}

{OPENING — 1 to 2 paragraphs}
State the core claim in the first sentence.
No lists. No code. No warm-up. The claim, then the context.
Connect to the previous section in exactly one sentence — make it subtle.

{CONCEPT — 2 to 4 paragraphs}
Explain from first principles.
Use an analogy if and only if the concept is genuinely abstract.
Keep paragraphs under 6 sentences.
No forbidden words (see style-guide.md Section 4).

{OPENTAION CONNECTION — exactly 1 paragraph}
Begin with one of the approved opening phrases from style-guide.md Section 5.
Be concrete. Name a specific file, function, or design decision.
This paragraph earns the concept's place in the book.

{CODE BLOCK — if this section has a milestone}
All four elements required: file path, context lines, run command, output.
See style-guide.md Section 6 for the exact format.
Code must have been verified in Step 2 before appearing here.

{WHAT JUST HAPPENED — 1 to 2 paragraphs}
Explain what the code does and why it was written that way.
Refer back to the concept. Close the loop.
Omit this block if the section has no code.

{CLOSING — exactly 1 paragraph}
Do not summarize. Create momentum toward the next section.
The reader should not want to stop here.
```

**Word count guidance:**
- Conceptual sections (no code): 400–700 words
- Milestone sections (with code): 600–1000 words
- Never go under 350 words — that is a stub, not a section
- Never go over 1200 words — that is two sections, not one

---

## Step 6: Self-Review

Read the completed section once before saving. Check:

- [ ] First sentence states a claim, not a topic
- [ ] No forbidden words from style-guide.md Section 4
- [ ] OpenTalon Connection paragraph is present and concrete
- [ ] If code exists: all four code block elements are present
- [ ] If code exists: you personally verified it runs
- [ ] Closing paragraph creates momentum, does not summarize
- [ ] Spelling: OpenTalon, Claude Code, BMAD, OpenRouter, Supabase, FastAPI
- [ ] Word count is within range

If any check fails, fix it before Step 7.

---

## Step 7: Update State Files

After the section passes self-review, update these files:

**1. `book/progress.md`**

In the Last Session block:
```
Date        : [today's date]
Completed   : Section {X.Y} — {title}. {One sentence describing what was argued.}
Stopped at  : End of {X.Y}. Prose complete. [Code verified / No code.]
Next target : Section {X.Z} — {next title from outline}
Open issues : [anything flagged during writing, or "None"]
```

In the progress table, change the section status from `○` to `●`.
If the section has a milestone, confirm it in the Milestone Summary table.

Update the Section Count at the bottom:
```
Completed : {previous count + 1}
Remaining : {110 - new completed count}
```

**2. `book/opentaion-state.md`** (only if code was written)

- Update the Current Version block with today's date and current section
- Change any `[TARGET]` markers to `[EXISTS]` for files that were created
- Add new functions to "Functions implemented" lists
- Fill in any external service details that were configured
- Add any new known issues discovered during implementation

---

## Step 8: Confirm to the User

When all steps are complete, report:

```
✓ Section {X.Y} written: "{Title}"
  Words        : {count}
  Code         : {verified / none}
  Milestone    : {reached: M{N} / not a milestone section}
  Files updated: progress.md {, opentaion-state.md if applicable}
  Next section : {X.Z} — "{Next title}"

  [Paste the first paragraph of the section here so the user
   can read the opening before deciding whether to continue.]
```

Then stop — **unless autonomous mode is active**.

Check `book/progress.md` Autonomous Mode Settings block:
- If `autonomous-mode: true` → proceed immediately to the next `○` section
  in the progress table without pausing. Do not report to the user between
  sections. Continue with Loop Step 2 of the `autonomous-write` skill.
- If `autonomous-mode: false` or the block is absent → stop here.
  The unit of work is one section. The human decides what comes next.
