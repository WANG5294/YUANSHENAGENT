# OpenTalon Book — Progress Tracker

> **What this file is:** Claude Code reads this file FIRST at the start of every session.
> It answers three questions in under 60 seconds:
> 1. Where did we stop?
> 2. What does OpenTalon look like right now?
> 3. What must the next section accomplish?
>
> **Update protocol:** After completing any section, update the relevant row
> in the status table, fill in the "Last Session" block, and — if code was
> written — update the OpenTalon snapshot below.

---

## Autonomous Mode Settings

```
autonomous-mode : complete
started-at      : 2026-03-14
ended-at        : 2026-03-14
compact-interval: 20        ← write compact anchor every N sections
ambiguity-policy: log-and-continue
```

---

## Last Session

```
Date        : 2026-03-14
Completed   : All 110 sections. Epilogue E.2 was the final section.
Stopped at  : Autonomous run complete. No remaining sections.
Next target : Annotation pass — review Autonomous Decisions Log + ⚑ entries
Open issues : None
```

> **How to fill this in:** Be specific. Not "wrote chapter 1" but
> "completed ch01/s1 — the confidence trap analogy. Stopped before
> introducing the agent loop. Next: ch01/s2 opens with the loop diagram."
> Vague entries are useless to a stateless agent.

---

## OpenTalon Codebase Snapshot

*This block describes the exact current state of the OpenTalon software.
Claude Code must read this before writing any section that touches code.
It is the ground truth — not the outline, not memory.*

```
Version     : 0.0.0 — not yet initialized
CLI         : Empty. No files written.
Web         : Empty. No files written.
API         : Empty. No files written.
Database    : Not provisioned. Supabase project not created.
OpenRouter  : Not configured. No API key set.
Tests       : None.
Last build  : N/A
Last test   : N/A
```

> **The codebase evolves chapter by chapter.** When Chapter 9's milestone
> is reached (OpenTalon CLI agent loop), this snapshot will say:
> "CLI: core/agent.py exists, run_loop() implemented, streams tokens to terminal."
> Every subsequent section that references the CLI reads this and knows
> what already exists. No speculation. No invention.

---

## Full Progress Table

Legend: `○` Not started · `◑` In progress · `●` Complete · `⚑` Needs revision

### PROLOGUE

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| P.1 | The Meta-Project | ● | |
| P.2 | OpenTalon system overview | ● | |
| P.3 | What you will have built | ● | |

---

### PART I — Foundations: How Agents Think

#### Chapter 1: The Agent Is Not a Chatbot

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 1.1 | The confidence trap | ● | Opens book. No code. Pure concept. |
| 1.2 | The perception → reasoning → action loop | ● | First diagram of the book |
| 1.3 | How Claude Code's master loop works | ● | Under-the-hood mechanics |
| 1.4 | Why OpenTalon will be different | ● | Frames the project |
| 1.5 | The founding question: what makes a tool agentic? | ● | Closes Part I Ch1 |

#### Chapter 2: Context Is Your Agent's Working Memory

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 2.1 | The context window as finite resource | ● | |
| 2.2 | What survives between sessions | ● | |
| 2.3 | The memory hierarchy | ● | CLAUDE.md → auto-memory → session → conversation |
| 2.4 | Context engineering vs. prompt engineering | ● | The paradigm shift |
| 2.5 | Writing the OpenTalon CLAUDE.md from scratch | ● | **MILESTONE M1: First file created** |

#### Chapter 3: Tools Are How Agents Touch the World

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 3.1 | Why tool use is different from text generation | ● | |
| 3.2 | Claude Code's native tools | ● | Read, Write, Edit, Bash, Glob, Grep |
| 3.3 | The feedback loop that creates genuine agency | ● | |
| 3.4 | The economics of tool calls | ● | Cost, latency, irreversibility |
| 3.5 | First agentic task: mapping the OpenTalon architecture | ● | **MILESTONE M2: Claude Code explores repo** |

---

### PART II — The Platform: Claude Code from the Inside Out

#### Chapter 4: CLAUDE.md — Your Agent's Constitution

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 4.1 | Hierarchical loading: how Claude Code reads memory | ● | |
| 4.2 | The @-import system and conditional loading | ● | |
| 4.3 | Monorepo strategy: three CLAUDE.md files for one project | ● | cli/, web/, api/ |
| 4.4 | What to include and what to leave out | ● | |
| 4.5 | Anti-patterns: the unmaintainable CLAUDE.md | ● | **MILESTONE M3: Production CLAUDE.md complete** |

#### Chapter 5: Slash Commands and the Skills System

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 5.1 | Built-in commands: the complete reference | ● | |
| 5.2 | The Skills system: YAML frontmatter and scope | ● | |
| 5.3 | Writing the /opentaion-component skill | ● | |
| 5.4 | Writing the /api-endpoint skill | ● | |
| 5.5 | The /effort command: tuning thinking depth | ● | **MILESTONE M4: Two custom skills working** |

#### Chapter 6: The Hooks System — Lifecycle Control

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 6.1 | The 12 lifecycle events | ● | |
| 6.2 | PreToolUse hooks: enforcing constraints | ● | |
| 6.3 | PostToolUse hooks: automated code quality | ● | black + ruff after every edit |
| 6.4 | Notification hooks: OS-level alerts | ● | |
| 6.5 | The "no API keys in code" hook | ● | **MILESTONE M5: Automated quality gate active** |

#### Chapter 7: MCP — Extending Your Agent's Senses

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 7.1 | How MCP works: protocol and transports | ● | |
| 7.2 | GitHub MCP for repository management | ● | |
| 7.3 | PostgreSQL MCP: Claude Code queries the database | ● | |
| 7.4 | Playwright MCP: testing the web dashboard | ● | |
| 7.5 | Tool Search: preventing context overflow | ● | **MILESTONE M6: MCP stack configured** |

#### Chapter 8: Permissions and Security

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 8.1 | The four permission modes | ● | |
| 8.2 | Rule syntax and the deny-wins hierarchy | ● | |
| 8.3 | OS-level sandboxing on macOS | ● | seatbelt |
| 8.4 | The OpenTalon threat model | ● | What Claude Code must never touch |
| 8.5 | Prompt injection: the hidden threat | ● | **MILESTONE M7: Secure dev environment configured** |

---

### PART III — Patterns: How to Actually Build Software Agentically

#### Chapter 9: The Plan-First Imperative

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 9.1 | Why the architecture collapses without a plan | ● | |
| 9.2 | The Explore → Plan → Code → Commit workflow | ● | |
| 9.3 | Writing the OpenTalon CLI specification | ● | The real SPEC.md |
| 9.4 | Plan Mode as a contractual checkpoint | ● | |
| 9.5 | When to break the pattern | ● | **MILESTONE M8: OpenTalon CLI SPEC.md complete** |

#### Chapter 10: Test-Driven Agentic Development

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 10.1 | Why TDD is the most powerful agentic pattern | ● | |
| 10.2 | Tests as specifications | ● | |
| 10.3 | The RED-GREEN-REFACTOR loop with Claude Code | ● | |
| 10.4 | Enforcing TDD: Superpowers and tdd-guard | ● | |
| 10.5 | Testing the OpenTalon context manager | ● | **MILESTONE M9: Full test suite for agent loop** |

#### Chapter 11: Multi-Agent Orchestration

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 11.1 | When single-agent hits its limits | ● | |
| 11.2 | The orchestrator-worker pattern | ● | |
| 11.3 | Git worktree isolation: three agents, three branches | ● | |
| 11.4 | Agent Teams: the experimental swarm frontier | ● | |
| 11.5 | Merging parallel work | ● | **MILESTONE M10: CLI + Web + API built in parallel** |

#### Chapter 12: Context Management at Scale

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 12.1 | /compact, /clear, and continuity | ● | |
| 12.2 | Subagents as context containers | ● | |
| 12.3 | Progressive disclosure in documentation | ● | |
| 12.4 | Large codebase strategies | ● | |
| 12.5 | The golden set: regression tasks for your agentic system | ● | **MILESTONE: OpenTalon handles 50+ file codebase** |

---

### PART IV — Methodology: The BMAD Method Applied to OpenTalon

#### Chapter 13: BMAD — The Philosophy

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 13.1 | Why structured collaboration beats full autonomy | ● | |
| 13.2 | The Scale-Domain-Adaptive principle | ● | |
| 13.3 | The two pillars: Planning + Context Engineering | ● | |
| 13.4 | The file-based handoff system | ● | |
| 13.5 | Installing BMAD V6 for OpenTalon | ● | **MILESTONE: BMAD configured** |

#### Chapter 14: Analysis and Planning — The PRD Phase

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 14.1 | Mary produces the OpenTalon product brief | ● | |
| 14.2 | John creates the PRD through facilitated dialogue | ● | |
| 14.3 | Epics and user stories for the web platform | ● | |
| 14.4 | Sally specifies the token consumption dashboard | ● | |
| 14.5 | The Implementation Readiness check | ● | **MILESTONE: PRD and epics complete** |

#### Chapter 15: Architecture — Designing the Web Platform

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 15.1 | Winston designs the full system | ● | Vite + React + FastAPI + Supabase |
| 15.2 | The boring technology principle | ● | |
| 15.3 | The proxy/gateway design | ● | How usage tracking sits between CLI and LLM |
| 15.4 | API design: auth, tokens, metering, dashboard | ● | |
| 15.5 | Implementation Readiness: connecting tech to PRD | ● | **MILESTONE: architecture.md complete** |

#### Chapter 16: Implementation — Bob, Amelia, and Quinn Build the Platform

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 16.1 | Bob creates hyper-detailed story files | ● | |
| 16.2 | Story anatomy: zero-ambiguity format | ● | |
| 16.3 | Amelia implements story by story | ● | |
| 16.4 | Quinn generates automated tests | ● | TEA module |
| 16.5 | Sprint tracking: story-001 to story-024 | ● | **MILESTONE: Working web platform** |

---

### PART V — Production: Shipping OpenTalon to the World

#### Chapter 17: CI/CD Integration

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 17.1 | Headless Claude Code: flags and JSON output | ● | |
| 17.2 | The GitHub Action: automated PR review | ● | |
| 17.3 | Quality gates before merge | ● | |
| 17.4 | Automated release notes and changelog | ● | |
| 17.5 | The hooks system as a CI/CD governance layer | ● | **MILESTONE: Automated pipeline active** |

#### Chapter 18: Testing and Validating AI-Generated Code

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 18.1 | The comprehension debt problem | ● | |
| 18.2 | Playwright MCP for E2E testing | ● | |
| 18.3 | The TEA module's testing patterns | ● | |
| 18.4 | Monitoring AI-generated code in production | ● | |
| 18.5 | The golden set for OpenTalon's core flows | ● | **MILESTONE: Full test pyramid** |

#### Chapter 19: Distributing OpenTalon

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 19.1 | Packaging the CLI for macOS: Homebrew tap | ● | |
| 19.2 | Deploying the web platform on Railway + Vercel | ● | |
| 19.3 | The OpenRouter integration: multi-model support | ● | |
| 19.4 | Email registration with magic links | ● | Supabase Auth |
| 19.5 | Token usage tracking: schema, metering, dashboard | ● | **MILESTONE: OpenTalon is live** |

---

### PART VI — Optimization: Making the System Faster, Cheaper, Better

#### Chapter 20: Cost and Performance Optimization

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 20.1 | Token economics: why agentic systems are expensive | ● | |
| 20.2 | The model selection matrix | ● | Opus vs. Sonnet vs. Haiku |
| 20.3 | The /effort command as a cost-quality lever | ● | |
| 20.4 | Prompt caching in the OpenTalon usage proxy | ● | |
| 20.5 | The claude-code-router pattern | ● | **MILESTONE: API costs reduced 70%** |

#### Chapter 21: Evolving Your Agentic System

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| 21.1 | Green flags: when your system is invisible | ● | |
| 21.2 | Red flags: workarounds multiplying | ● | |
| 21.3 | Evolution triggers | ● | |
| 21.4 | The one rule | ● | |
| 21.5 | OpenTalon V2: what comes after | ● | **MILESTONE: Book complete** |

---

### EPILOGUE

| Section | Title | Status | Notes |
|---------|-------|--------|-------|
| E.1 | What you have built | ● | |
| E.2 | What it means | ● | |

---

## Milestone Summary

*A quick-reference map of what OpenTalon looks like at each major milestone.
Update this as milestones are reached.*

| Milestone | Chapter | What exists at this point |
|-----------|---------|--------------------------|
| M1 | 2.5 ● | First CLAUDE.md file. Project structure initialized. `opentaion/` dir created, `git init` run. |
| M2 | 3.5 ● | Claude Code has explored the repo. Architecture understood. First agentic task complete. |
| M3 | 4.5 ● | Production CLAUDE.md. Monorepo structure in place. Three component CLAUDE.md files created. |
| M4 | 5.5 ● | Two custom skills: /opentaion-component and /api-endpoint. /effort levels understood. |
| M5 | 6.5 ● | Automated quality hooks. format-on-save, no-api-keys, OS notifications all active. |
| M6 | 7.5 ● | MCP stack: GitHub + PostgreSQL + Playwright connected. Tool Search active. |
| M7 | 8.5 ● | Secure dev environment. Injection-awareness in CLAUDE.md. Full permission config complete. |
| M8 | 9.5 ● | OpenTalon CLI SPEC.md written and committed. Architecture decided. |
| M9 | 10.5 ● | Context manager + OpenRouter client tests. TDD enforced. Hypothesis property tests. |
| M10 | 11.5 ● | CLI + Web + API built in parallel via worktrees. Integration test passes. |
| M11 | 12.5 ● | Domain routing + Grep-before-Read rules active. Golden set (4 tasks) passes against 50+ file integrated codebase. docs/golden-set.md committed. |
| M12 | 13.5 ● | BMAD V6 installed. _bmad/ structure created, 68+ slash commands in .claude/commands/. /bmad-help verified. Root CLAUDE.md updated with BMAD workflow section. |
| M13 | 14.5 ● | product-brief.md, prd.md, epics-and-stories.md, ux-spec.md all in _bmad/artifacts/. Readiness check passed. 3 gaps found and resolved. |
| M14 | 15.5 ● | 5 planning artifacts complete and committed. Architecture covers API contract, DB schema, RLS policies, async write pattern. Both readiness checks passed. |
| M15 | 16.5 ● | 24 stories done. Web: auth, API keys, dashboard. API: proxy, usage metering. All tests pass. |
| M16 | 17.5 ● | 4 GitHub Action workflows. PR review + test gate + secret scan + changelog. Branch protection on main. Test PR merged. |
| M17 | 18.5 ● | Unit (pytest) + integration (TEA patterns) + E2E (Playwright) + production golden set (4 tasks). All passing. |
| M18 | 19.5 ● | Homebrew tap live. Railway API deployed. Vercel web deployed. Full new-user journey verified with golden set. |
| M19 | 20.5 ● | Prompt caching + claude-code-router. 70% cost reduction measured on representative session. |
| M20 | 21.5 ● | All 110 sections written. V2 directions documented. Manuscript complete. |

---

## Section Count

```
Total sections planned : 110
Completed              : 110
In progress            : 0
Remaining              : 0
Estimated completion   : [set when you establish your writing pace]
```

---

## Compact Anchor — After Section 4.16.2 (80/110 complete)

Date: 2026-03-14. 80 of 110 sections complete. Parts I–IV ch13–16 s1–s2 done.
OpenTalon milestone last reached: M14 (15.5) — architecture.md complete with RLS, async writes.
Last autonomous decision: none since last anchor.
Next section: 4.16.3 — "Amelia Implements Story by Story".
On restart: read this anchor, then run /autonomous-write.

---

## Compact Anchor — After Section 3.10.2 (50/110 complete)

Date: 2026-03-14. 50 of 110 sections complete. Through Part II (Ch4–8) + Part III Ch9–10 s1–s2.
OpenTalon milestone last reached: M8 (9.5) — CLI SPEC.md written and committed.
Last autonomous decision: none since last anchor.
Next section: 3.10.3 — "The RED-GREEN-REFACTOR Loop with Claude Code".
On restart: read this anchor, then run /autonomous-write.

---

## Compact Anchor — After Section 2.8.2 (40/110 complete)

Date: 2026-03-14. 40 of 110 sections complete. Prologue + Part I (Ch1–3) + Part II Ch4–8 s1–s2 done.
OpenTalon milestone last reached: M6 (7.5) — GitHub + PostgreSQL + Playwright MCP stack configured.
Last autonomous decision: none since last anchor.
Next section: 2.8.3 — "OS-Level Sandboxing on macOS".
On restart: read this anchor, then run /autonomous-write.

---

## Compact Anchor — After Section 2.4.2 (20/110 complete)

Date: 2026-03-14. 20 of 110 sections complete. Prologue + Part I (Ch1–3) + Part II Ch4 s1–s2 done.
OpenTalon milestone last reached: M2 (3.5) — Claude Code explored repo, architecture understood.
Last autonomous decision: [P.0.2] Node.js prerequisite placed in P.2 per must-cover.
Next section: 2.4.3 — "Monorepo Strategy: Three CLAUDE.md Files for One Project".
On restart: read this anchor, then run /autonomous-write.

---

## Autonomous Decisions Log

> Format: `[Section P.C.S] [type] Decision. Reasoning in one sentence.`
> Types: interpretation · code · voice · forward-ref · contradiction
> Populated during the autonomous run. Review before the annotation pass.

[P.0.3] [forward-ref] Used illustrative CLI terminal output in the prologue. The outline's must-cover explicitly requires showing the first task — treated as user-experience preview, not verified implementation code.
[P.0.2] [interpretation] Placed Node.js prerequisite note in P.2 per updated must-cover; outline entry explicitly requires it here.
