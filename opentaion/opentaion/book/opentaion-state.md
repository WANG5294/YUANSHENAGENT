# OpenTalon — Codebase State

> **What this file is:** The ground truth about what OpenTalon actually is
> right now — not what the outline says it will be, not what the last chapter
> described, but what exists on disk at this moment.
>
> **Who reads this:** Claude Code reads this before writing any section that
> touches code. It is the single source of truth that prevents speculative
> code — writing functions that reference files that don't exist yet, or
> importing modules that haven't been built.
>
> **Who updates this:** Claude Code updates this file immediately after any
> section that creates, modifies, or deletes files in the OpenTalon repository.
> The update happens before the session ends. A stale state file is worse
> than no state file.
>
> **Format discipline:** Every section of this file uses the same structure.
> Do not add narrative. Do not explain decisions here — that belongs in the
> book. This file is a map, not an essay. Keep it scannable.

---

## Current Version

```
OpenTalon version  : 0.0.0-prereq
Last updated       : [not started]
Last milestone     : None — project not yet initialized
Next milestone     : M1 (Chapter 2.5) — First CLAUDE.md, project structure
Book section       : Not started
```

---

## Repository Root

```
Status: NOT INITIALIZED
```

The repository does not exist yet. No files have been created.
The structure below is the target — what will exist when the book is complete.
Sections marked `[TARGET]` are planned but not built.
Sections marked `[EXISTS]` have been created.

When a file is created during a writing session, change its marker from
`[TARGET]` to `[EXISTS]` and fill in the details below.

---

## Repository Structure (Target → Actual)

```
opentaion/                          [TARGET]
├── CLAUDE.md                       [TARGET] ← project-level agent constitution
├── pyproject.toml                  [TARGET] ← uv project config
├── .env.example                    [TARGET] ← env var template
├── .gitignore                      [TARGET]
│
├── cli/                            [TARGET] ← OpenTalon CLI (Python)
│   ├── CLAUDE.md                   [TARGET] ← CLI-specific agent rules
│   ├── pyproject.toml              [TARGET]
│   ├── src/
│   │   └── opentaion/
│   │       ├── __main__.py         [TARGET] ← entry point: `python -m opentaion`
│   │       ├── agent.py            [TARGET] ← core agent loop
│   │       ├── tools.py            [TARGET] ← file/bash/search tools
│   │       ├── context.py          [TARGET] ← context window manager
│   │       ├── llm.py              [TARGET] ← OpenRouter client
│   │       ├── config.py           [TARGET] ← config loader (.env + flags)
│   │       └── display.py          [TARGET] ← Rich terminal UI
│   └── tests/
│       ├── test_agent.py           [TARGET]
│       ├── test_context.py         [TARGET]
│       └── test_tools.py           [TARGET]
│
├── web/                            [TARGET] ← OpenTalon Web (Vite + React + Tailwind)
│   ├── CLAUDE.md                   [TARGET] ← web-specific agent rules
│   ├── package.json                [TARGET]
│   ├── vite.config.ts              [TARGET]
│   ├── tailwind.config.ts          [TARGET]
│   ├── src/
│   │   ├── main.tsx                [TARGET]
│   │   ├── App.tsx                 [TARGET] ← renders <Login> or <Dashboard> based on auth state (no router)
│   │   ├── Login.tsx               [TARGET] ← email input + magic link form
│   │   ├── Dashboard.tsx           [TARGET] ← tab nav: Usage | API Keys (conditional render, no router)
│   │   ├── UsageChart.tsx          [TARGET] ← Recharts bar chart (daily token usage)
│   │   ├── ApiKeyList.tsx          [TARGET] ← list + create + revoke keys
│   │   └── lib/
│   │       ├── supabase.ts         [TARGET] ← Supabase client + auth helpers
│   │       └── api.ts              [TARGET] ← typed fetch wrapper for OpenTalon API
│   └── tests/
│       └── e2e/                    [TARGET] ← Playwright tests
│
├── api/                            [TARGET] ← OpenTalon API (FastAPI)
│   ├── CLAUDE.md                   [TARGET] ← API-specific agent rules
│   ├── pyproject.toml              [TARGET]
│   ├── src/
│   │   └── opentaion_api/
│   │       ├── main.py             [TARGET] ← FastAPI app entry point
│   │       ├── routers/
│   │       │   ├── auth.py         [TARGET] ← registration, magic links
│   │       │   ├── keys.py         [TARGET] ← API key CRUD
│   │       │   ├── proxy.py        [TARGET] ← LLM proxy + usage metering
│   │       │   └── usage.py        [TARGET] ← usage query endpoints
│   │       ├── models/
│   │       │   ├── user.py         [TARGET] ← SQLAlchemy User model
│   │       │   ├── api_key.py      [TARGET] ← APIKey model
│   │       │   └── usage_log.py    [TARGET] ← UsageLog model
│   │       ├── db.py               [TARGET] ← Supabase/PostgreSQL connection
│   │       └── config.py           [TARGET] ← settings from env
│   ├── alembic/                    [TARGET] ← database migrations
│   └── tests/
│       ├── test_auth.py            [TARGET]
│       ├── test_proxy.py           [TARGET]
│       └── test_usage.py           [TARGET]
│
└── .claude/                        [TARGET] ← Claude Code configuration
    ├── skills/
    │   ├── write-section/
    │   │   └── SKILL.md            [EXISTS] ← book writing skill
    │   ├── session-wrap/
    │   │   └── SKILL.md            [EXISTS] ← end-of-session state capture
    │   ├── autonomous-write/
    │   │   └── SKILL.md            [EXISTS] ← autonomous multi-section writing
    │   ├── opentaion-component/
    │   │   └── SKILL.md            [TARGET] ← scaffold a new CLI command
    │   └── api-endpoint/
    │       └── SKILL.md            [TARGET] ← scaffold a FastAPI route
    └── hooks/
        ├── settings.json           [TARGET] ← hook configuration
        └── no-api-keys.sh          [TARGET] ← blocks API keys in code
```

---

## Component Status

### CLI — Python Agent

```
Status          : NOT STARTED
Language        : Python 3.12+
Package manager : uv
Entry point     : python -m opentaion "prompt here"
Current version : n/a

Files that exist:
  (none)

Functions implemented:
  (none)

Known working:
  (none)

Blockers / open questions:
  (none yet — will populate as build progresses)
```

---

### Web — Vite + React + Tailwind

```
Status          : NOT STARTED
Framework       : Vite 5.x + React 18 + TypeScript
Styling         : Tailwind CSS 3.x (utility classes directly, no component library)
Charts          : Recharts
Routing         : none — conditional rendering on Supabase auth state (no React Router)

Files that exist:
  (none)

Pages implemented:
  (none)

Components implemented:
  (none)

Known working:
  (none)
```

---

### API — FastAPI

```
Status          : NOT STARTED
Framework       : FastAPI 0.110+
ORM             : SQLAlchemy 2.x (async)
Migrations      : Alembic

Files that exist:
  (none)

Endpoints implemented:
  (none)

Models defined:
  (none)

Known working:
  (none)
```

---

### Database — Supabase

```
Status          : NOT PROVISIONED
Provider        : Supabase (PostgreSQL)
Project name    : opentaion (to be created)
Region          : [choose closest to you on signup]

Tables that exist:
  (none)

Migrations run:
  (none)

Connection string:
  postgresql+asyncpg://[user]:[password]@[host]:5432/postgres
  (fill in when Supabase project is created)

Supabase Auth:
  Magic links: NOT CONFIGURED
  Email templates: NOT CONFIGURED
```

---

### External Services

```
OpenRouter
  Status        : NOT CONFIGURED
  Account       : [create free account at openrouter.ai]
  API key       : NOT SET
  Models in use : (none yet — will use free tier models)
  Free models available (as of book writing):
    - deepseek/deepseek-r1          (reasoning, free)
    - meta-llama/llama-3.3-70b      (general, free)
    - mistralai/mistral-7b          (fast, free)
    - google/gemma-3-27b-it         (capable, free)

Railway (API deployment)
  Status        : NOT PROVISIONED
  Service name  : opentaion-api (to be created)
  URL           : (will be assigned on first deploy)

Vercel (Web deployment)
  Status        : NOT PROVISIONED
  Project name  : opentaion-web (to be created)
  URL           : (will be assigned on first deploy)

Homebrew Tap (CLI distribution)
  Status        : NOT CREATED
  Tap name      : [yourgithub]/homebrew-opentaion (to be created)
  Formula       : opentaion.rb (to be created)
```

---

## Environment Variables

```
# These are the env vars OpenTalon needs.
# None are set yet. Fill in as each service is provisioned.
# NEVER commit real values. Use .env.example for the template.

# OpenRouter
OPENROUTER_API_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=

# OpenTalon API
API_SECRET_KEY=        ← generate with: python -c "import secrets; print(secrets.token_hex(32))"
API_BASE_URL=          ← http://localhost:8000 in dev, Railway URL in prod

# OpenTalon CLI
OPENTAION_API_KEY=     ← issued by the web platform after registration
OPENTAION_API_URL=     ← same as API_BASE_URL, set by user after signup
OPENTAION_MODEL=       ← defaults to deepseek/deepseek-r1 if not set
```

---

## Data Models

```
Status: NOT DEFINED

Target schema (to be implemented in Chapter 15-16):

User
  id            UUID PRIMARY KEY
  email         TEXT UNIQUE NOT NULL
  created_at    TIMESTAMPTZ DEFAULT NOW()
  is_active     BOOLEAN DEFAULT TRUE

APIKey
  id            UUID PRIMARY KEY
  user_id       UUID REFERENCES User(id)
  key_hash      TEXT NOT NULL          ← bcrypt hash, never store plaintext
  key_prefix    TEXT NOT NULL          ← first 8 chars, shown in dashboard
  name          TEXT                   ← user-assigned label
  created_at    TIMESTAMPTZ DEFAULT NOW()
  last_used_at  TIMESTAMPTZ
  is_active     BOOLEAN DEFAULT TRUE

UsageLog
  id            UUID PRIMARY KEY
  api_key_id    UUID REFERENCES APIKey(id)
  model         TEXT NOT NULL          ← e.g. "deepseek/deepseek-r1"
  prompt_tokens INT NOT NULL
  completion_tokens INT NOT NULL
  total_tokens  INT NOT NULL
  cost_usd      NUMERIC(10,6)          ← may be 0.000000 for free models
  created_at    TIMESTAMPTZ DEFAULT NOW()
  request_ms    INT                    ← latency in milliseconds
```

---

## API Endpoints

```
Status: NOT IMPLEMENTED

Target endpoints (to be implemented in Chapter 15-16):

Auth
  POST /auth/register          ← email → magic link sent
  POST /auth/verify            ← token → session created
  POST /auth/logout            ← session invalidated

API Keys
  GET  /keys                   ← list user's active keys
  POST /keys                   ← create new key → returns plaintext once
  DELETE /keys/{id}            ← revoke key

Proxy (the core of the platform)
  POST /v1/chat/completions    ← OpenAI-compatible, metered, proxied to OpenRouter

Usage
  GET  /usage/summary          ← total tokens, cost, requests (last 30 days)
  GET  /usage/daily            ← daily breakdown for dashboard chart
  GET  /usage/by-model         ← breakdown by model
```

---

## Test Coverage

```
CLI tests
  Unit tests    : 0 / 0 planned
  Coverage      : n/a

API tests
  Unit tests    : 0 / 0 planned
  Integration   : 0 / 0 planned
  Coverage      : n/a

Web tests
  E2E (Playwright) : 0 / 0 planned
  Coverage         : n/a
```

---

## Known Issues and Technical Debt

```
(None yet — will populate as build progresses)

Format when adding an issue:
  [CHAPTER INTRODUCED] [SEVERITY: low/medium/high] Description
  Example:
  [Ch 10] [medium] Context manager does not handle token count
           estimation for tool outputs — uses rough heuristic.
           Needs proper tokenizer integration before Chapter 12.
```

---

## How to Update This File

After any section that creates or modifies code, update:

1. **Current Version block** — bump version if a milestone was reached,
   update "Last updated" and "Book section"

2. **Repository Structure** — change `[TARGET]` to `[EXISTS]` for any
   file that was created

3. **Component Status** — add to "Files that exist" and
   "Functions implemented" lists

4. **External Services** — fill in any URLs, project names, or config
   that was set up during the session

5. **Test Coverage** — update counts when tests are written

6. **Known Issues** — add any technical debt or open questions
   that emerged during implementation

One rule: **update this file before ending the session.**
A state file that is one session behind is a trap for the next session.
