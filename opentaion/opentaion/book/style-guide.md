# OpenTalon Book — Style Guide

> **What this file is:** The writing bible. Claude Code reads this at the
> start of the first writing session each day, then keeps it in working memory.
> It governs every word, sentence, paragraph, code block, and structural
> decision in the book. When in doubt, come back here.
>
> **Priority:** When this file conflicts with an instinct to write something
> that "sounds better," this file wins. Voice consistency over 110 sections
> written across many months requires rules that override taste in the moment.

---

## 1. The Author's Voice

### Who is speaking?

The author is a **senior agentic engineer at Anthropic** who has spent years
building production systems with Claude Code. She is not a teacher. She is a
practitioner who has agreed to write down what she knows.

This distinction matters. A teacher simplifies for the student.
A practitioner shares hard-won knowledge with a peer who is capable of
handling the truth — including the uncomfortable parts.

The reader is a **solo developer** — technically competent, probably has
shipped at least one product, and is new to agentic systems but not to
engineering. She does not need protecting from complexity. She needs
complexity explained clearly.

### The single test for every sentence

Read the sentence aloud. Ask: *Would a senior engineer say this to a colleague
over coffee, or does it sound like a blog post?*

Blog post voice (wrong):
> "In today's rapidly evolving AI landscape, developers are discovering
> powerful new ways to leverage cutting-edge tools."

Senior engineer voice (right):
> "Most developers use Claude Code like a faster autocomplete.
> That's not wrong — it's just leaving most of the value on the table."

If it sounds like a blog post, rewrite it.

---

## 2. Tone Spectrum

The book lives in a specific band of the tone spectrum. It never goes outside it.

```
← Too casual          In band              Too formal →
chatty / breezy  [direct / honest / dry]  academic / stiff
```

**Direct** means: make the claim, then support it. No warm-up.

Wrong:
> "Before we dive into the main topic of this section, it might be
> helpful to first consider why this matters."

Right:
> "The context window is not a feature. It is a constraint that shapes
> every architectural decision you will make with Claude Code."

**Honest** means: name the limitations, costs, and failure modes. Do not sell.

Wrong:
> "Claude Code's powerful multi-agent system enables seamless parallel
> development across your entire codebase."

Right:
> "Multi-agent orchestration roughly doubles your token costs and adds
> coordination overhead. It is worth it when tasks are genuinely independent.
> It is not worth it when you are just impatient."

**Dry** means: occasional wit is welcome. Jokes are not.

Acceptable:
> "Bob the Scrum Master writes story files with zero tolerance for ambiguity.
> He is, in this way, the most useful fictional person in software engineering."

Not acceptable:
> "Bob is basically the Marie Kondo of sprint planning — does this story spark
> clarity? If not, thank it and rewrite it!"

---

## 3. Sentence and Paragraph Rules

### Sentences

**Length variation is mandatory.** A paragraph of uniformly medium-length
sentences reads like a machine wrote it. Vary deliberately:

```
Short sentence. Then a medium-length sentence that adds context or nuance.
Then, occasionally, a longer sentence that works through something complex
step by step, building to a conclusion the reader feels arriving.
Short again.
```

**Active voice as the default.** Passive voice is permitted when the actor
is genuinely unknown or irrelevant. It is not permitted as a way to sound
more formal or to avoid taking a position.

Wrong: "Errors are handled by returning False."
Right: "The function returns False when the database query fails."

**One idea per sentence.** Split sentences joined by "and" or "but" when
each clause would stand alone.

Weak: "The agent loop runs until the model produces no tool calls and then
returns control to the user and this is where you can inspect the result."

Strong: "The agent loop runs until the model produces no tool calls.
At that point, control returns to you. That pause is your inspection window."

### Paragraphs

**Four to six sentences is the target length.** Shorter is fine for emphasis.
Longer signals that two ideas are being conflated.

**First sentence states the claim.** Not a question. Not a transition. The claim.

Wrong: "In this section, we will explore why context management matters."
Right: "Context management is the skill that separates agentic engineering
from vibe coding."

**No orphan sentences.** Every sentence must connect to the one before it
and the one after it. If a sentence could be deleted without the paragraph
losing meaning, delete it.

---

## 4. Forbidden Words and Phrases

These words and phrases are banned. They appear in every AI-generated text
and every mediocre technical blog. Their presence signals that the author
stopped thinking.

| Banned | Why | Replace with |
|--------|-----|--------------|
| powerful | Empty intensifier | Name the specific capability |
| seamless | Marketing language | Describe the actual experience |
| leverage | Jargon for "use" | Use |
| robust | Means nothing | Specific: "handles malformed input without crashing" |
| straightforward | Condescending | Just say what it is |
| simply / just | Condescending | Delete the word entirely |
| obviously / of course | Condescending | Delete |
| it is worth noting that | Filler | Delete, say the thing |
| in today's X landscape | Blog opening | Delete, start with the claim |
| delve | Overused AI word | Examine, explore, look at |
| as we can see | Filler | Delete |
| take a deep dive | Cliché | Delete, just go deep |
| cutting-edge / state-of-the-art | Marketing | Name the specific thing |
| game-changer | Marketing | Delete |
| revolutionary | Marketing | Delete |
| at the end of the day | Filler | Delete |
| in conclusion | Never use this | Just conclude |
| synergy | No | No |

---

## 5. The OpenTalon Connection Rule

Every section — without exception — must contain a paragraph that explicitly
connects the concept being explained to OpenTalon.

This paragraph follows the concept explanation and precedes any code.
It opens with one of these phrases (vary them, do not repeat the same one
more than twice per chapter):

- "In OpenTalon, this means..."
- "For our project, this translates to..."
- "Watch how this plays out when we build..."
- "OpenTalon confronts this problem directly when..."
- "This is not abstract for us — in Chapter [X], when we build [Y]..."

**Why this rule is non-negotiable:** Project-based learning books fail when
readers cannot answer the question "why am I learning this?" The OpenTalon
Connection paragraph answers that question every single time, for every single
concept. If you cannot write this paragraph for a concept, the concept does
not belong in the book.

---

## 6. Code Block Standards

### Every code block needs four things

**1. File path header** — where does this live in the repository?
```
# opentaion/cli/core/agent.py
```

**2. Context lines** — 3–5 lines before and after the relevant change,
marked with a comment if it is a modification:
```python
# opentaion/cli/core/agent.py

import httpx
from rich.console import Console
from .config import Config

# --- NEW: async agent loop ---
async def run(prompt: str, config: Config) -> None:
    console = Console()
    async with httpx.AsyncClient() as client:
        await _loop(prompt, client, console, config)
```

**3. Run command** — how do you execute this?
```bash
cd opentaion/cli
uv run python -m opentaion "what files are in this directory?"
```

**4. Expected output** — what does success look like?
```
✓ OpenTalon v0.1.0  model: deepseek/deepseek-r1  context: 8,204 tokens
→ Analyzing request...
→ Reading directory...
  auth.py  config.py  agent.py  __main__.py
✓ Done  (3 tool calls · 0.8s · $0.00)
```

### When to use code blocks

Use code blocks for:
- Any code the reader must type or copy
- File contents the reader must create
- Terminal commands
- Expected output
- Configuration files (CLAUDE.md, settings.json, pyproject.toml)

Do not use code blocks for:
- Pseudocode described in prose
- File paths mentioned in a sentence
- Single function or variable names (use `backticks` instead)

### Inline code formatting

Use `backticks` for: file names (`agent.py`), function names (`run_loop()`),
command names (`/compact`), flags (`--max-turns`), and short code snippets
that appear inside a sentence.

Do not use backticks for: tool names (Claude Code), product names (OpenTalon),
or acronyms (MCP, CLI) unless they are specifically the command or flag name.

---

## 7. Structural Elements

### Headers

The book uses three levels of headers inside a section file:

```markdown
## Section X.Y: Title        ← The section title (one per file)
### Subsection heading        ← A major division within the section
#### A specific topic         ← Use sparingly, only when necessary
```

Never use H1 (`#`) inside a section file. H1 is reserved for the chapter
title in the chapter index file.

Never use bold text as a substitute for a header. If something is important
enough to be a header, make it a header.

### Lists

Use bulleted lists for:
- Items with no inherent order
- Three or more items that would create a run-on sentence in prose
- Reference material (command flags, options, parameters)

Use numbered lists for:
- Steps that must happen in sequence
- Ranked items where order carries meaning

**Never use lists as a substitute for prose.** A section that is mostly lists
is a section that was not fully thought through. Lists present information.
Prose explains it. The book needs both, but prose carries the argument.

Wrong (list as lazy prose):
> The agent loop works because:
> - It perceives the environment
> - It reasons about what to do
> - It takes action
> - It observes the result

Right (prose with a list):
> The agent loop is a closed feedback cycle. The agent perceives the
> environment through its tools — reading files, running commands,
> searching the web. It reasons about what it observes. It acts.
> Then it perceives again, now with the result of its action in context.
> This cycle — perceive, reason, act, observe — is what distinguishes
> an agent from a function that runs once and returns.

### Callout blocks

Use blockquote formatting for three specific purposes only:

**Insight** — a conclusion the reader should carry forward:
> The context window is not a feature. It is a budget.

**Warning** — something that will cause real pain if ignored:
> **Warning:** The `bypassPermissions` mode skips all safety checks.
> Never use it outside an isolated sandbox. On a development machine
> with real credentials, it is a loaded gun.

**Definition** — when introducing a term for the first time:
> **Agentic loop:** The repeated cycle of perception, reasoning, and action
> that continues until the model produces a response with no tool calls.

Do not use callout blocks for general emphasis or to highlight things
you found interesting. Use them only for the three purposes above.

---

## 8. Transitions Between Sections

The last paragraph of every section must do two things:

1. Close the current idea — do not summarize everything that was just said,
   just land the final point cleanly
2. Create momentum toward the next section — one sentence that makes the
   reader want to continue

**Wrong closing (summary):**
> "In this section, we covered the agent loop, the role of tool calls,
> and why the feedback cycle is what makes Claude Code agentic. We also
> saw how this applies to OpenTalon."

**Right closing (momentum):**
> "The loop exists. Now it needs something to loop over — and what it
> loops over is determined entirely by what tools you give it access to."

The reader should not want to stop at the end of a section. They should
want to read the next one.

---

## 9. Handling Difficulty and Controversy

### When something is genuinely hard

Name it. Do not soften it.

Wrong: "Context management can sometimes be a bit tricky."
Right: "Context management is the hardest part of agentic engineering.
There is no clean solution — only trade-offs."

Then explain the trade-offs clearly and tell the reader which one to choose
for the OpenTalon use case, and why.

### When Claude Code has real limitations

Name them. This book is written by a practitioner, not a promoter.

Examples of honest statements this book makes:
- "Multi-agent orchestration roughly doubles your token costs."
- "The METR randomized controlled trial found that AI tools made experienced
  developers 19% slower on familiar codebases. The perception of speed and
  the reality of speed are different things."
- "Fully autonomous agents succeed on roughly 15% of complex real-world tasks.
  The rest require human intervention."

Readers trust authors who tell them the truth. They distrust authors who
only say positive things. Honest limitation statements make the positive
claims more credible.

### When there are multiple valid approaches

Present the options, state the trade-offs, and make a recommendation.
Do not end with "it depends on your use case" as a substitute for a
recommendation. The reader came to us because they want guidance.

Wrong:
> "You could use Sonnet or Opus for this task. Both have their merits.
> Ultimately, it depends on your specific needs and budget."

Right:
> "Use Sonnet for implementation tasks — it is 5× cheaper than Opus and
> the quality difference is negligible for well-specified work. Use Opus
> when you need to reason through architecture: ambiguous constraints,
> conflicting requirements, or decisions you cannot easily reverse.
> For OpenTalon, that means Opus writes the SPEC.md and Sonnet writes
> the code."

---

## 10. The Numbers Rule

**Always be specific.** Vague numbers destroy credibility.
Specific numbers build it — even when the numbers are estimates.

Wrong: "This reduces token usage significantly."
Right: "This reduces token usage by approximately 60–80%, depending on
how much of the conversation was tool output versus reasoning."

Wrong: "The context window is large."
Right: "Claude Code's default context window is 200K tokens —
roughly 150,000 words, or about twice the length of this book."

Wrong: "Running multiple agents costs more."
Right: "A three-agent parallel workflow typically costs 2.5–3× more
than a single-agent workflow for the same task, because each agent
maintains its own context and the orchestrator adds coordination overhead."

When you do not know the exact number, say so and give a range:
"Roughly 10–20× more tokens than a single-turn interaction,
depending on task complexity and how many self-correction loops occur."

---

## 11. Chapter and Section Naming

### Chapter titles

Chapter titles are declarative statements, not questions or labels.

Wrong: "Understanding Context Windows"
Wrong: "What Is Context Management?"
Right: "Context Is Your Agent's Working Memory"

The title should be something the reader could argue with or agree with.
"Understanding Context Windows" is a label — no one can disagree with it.
"Context Is Your Agent's Working Memory" is a claim. Claims create engagement.

### Section titles

Section titles are shorter and more specific than chapter titles.
They name what the section does, not what it covers.

Wrong: "The Agent Loop"
Right: "How Claude Code's Master Loop Works"

Wrong: "Security"
Right: "The Threat Hidden in README Files"

---

## 12. The Consistency Checklist

Before submitting any section, verify:

- [ ] OpenTalon is spelled consistently: **OpenTalon** (capital O, capital T)
- [ ] The CLI tool is referred to as **OpenTalon CLI** (not "the CLI" on first mention in a section)
- [ ] Claude Code is **Claude Code** (two words, both capitalized, no "the" needed)
- [ ] BMAD agents are referred to by name: **Mary**, **John**, **Sally**, **Winston**, **Bob**, **Amelia**, **Quinn**
- [ ] The tech stack is consistent with CLAUDE.md Section 4 (Vite + Tailwind, FastAPI, Supabase, OpenRouter)
- [ ] File paths use the repository structure from CLAUDE.md Section 2
- [ ] No forbidden words from Section 4 of this guide
- [ ] Every section has exactly one OpenTalon Connection paragraph
- [ ] Code blocks have all four required elements (path, context, run command, expected output)
- [ ] The closing paragraph creates momentum, not a summary

---

## 13. One Final Rule

**Write the section you would want to read.**

Not the section that covers all the material. Not the section that ticks
every box in the outline. The section that makes a senior developer stop
skimming and actually read.

If you would not read it — rewrite it.
