# Spec-Driven Development — GitHub Copilot Instructions

> Based on the TLC Spec-Driven methodology by Tech Leads Club.
> Reference: https://agent-skills.techleads.club/skills/tlc-spec-driven/

---

## Core Workflow: SPECIFY → DESIGN → TASKS → EXECUTE

```
┌──────────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐
│ SPECIFY  │ → │  DESIGN  │ → │  TASKS  │ → │ EXECUTE │
└──────────┘   └──────────┘   └─────────┘   └─────────┘
   required      optional*      optional*     required

* Auto-skip when scope doesn't need it
```

**You MUST follow this workflow for every feature or significant change.**

---

## Auto-Sizing: Match Depth to Complexity

Before starting, assess scope and apply only what's needed:

| Scope | What | Specify | Design | Tasks | Execute |
|-------|------|---------|--------|-------|---------|
| **Small** | ≤3 files, one sentence | Quick mode — skip pipeline | — | — | — |
| **Medium** | Clear feature, <10 tasks | Spec (brief) | Skip (inline) | Skip (implicit) | Implement + verify |
| **Large** | Multi-component | Full spec + requirement IDs | Architecture + components | Full breakdown + dependencies | Implement + verify per task |
| **Complex** | Ambiguous, new domain | Full spec + discuss gray areas | Research + architecture | Breakdown + parallel plan | Implement + interactive UAT |

**Rules:**
- Specify and Execute are ALWAYS required
- Design is skipped when straightforward (no architectural decisions)
- Tasks is skipped when ≤3 obvious steps
- Safety valve: Even when Tasks is skipped, Execute ALWAYS starts by listing atomic steps inline. If >5 steps emerge, STOP and create `tasks.md`

---

## Project Structure

All documentation lives in `.specs/`:

```
.specs/
├── project/
│   ├── PROJECT.md      # Vision & goals
│   ├── ROADMAP.md      # Features & milestones
│   └── STATE.md        # Memory: decisions, blockers, lessons, todos, deferred ideas
├── codebase/           # Brownfield analysis (existing projects)
│   ├── STACK.md
│   ├── ARCHITECTURE.md
│   ├── CONVENTIONS.md
│   ├── STRUCTURE.md
│   ├── TESTING.md
│   ├── INTEGRATIONS.md
│   └── CONCERNS.md
├── features/           # Feature specifications
│   └── [feature-slug]/
│       ├── spec.md     # Requirements with traceable IDs
│       ├── context.md  # User decisions for gray areas (only when needed)
│       ├── design.md   # Architecture & components (Large/Complex only)
│       └── tasks.md    # Atomic tasks with verification (Large/Complex only)
└── quick/              # Ad-hoc tasks (quick mode)
    └── NNN-slug/
        ├── TASK.md
        └── SUMMARY.md
```

---

## Context Loading Strategy

**Always load at session start:**
- `.specs/project/STATE.md` — persistent memory
- `.specs/project/PROJECT.md` — project vision

**Load on-demand:**
- `ROADMAP.md` — when planning or working on features
- Codebase docs — when working in existing project
- `CONCERNS.md` — when touching flagged/risky areas
- `TESTING.md` — when creating tasks or executing
- Feature `spec.md` / `design.md` / `tasks.md` — when working on that feature

**Never load simultaneously:** multiple feature specs, multiple architecture docs.

---

## Phase 1 — SPECIFY

**Goal:** Capture WHAT to build with testable, traceable requirements.

**Process:**
1. Clarify requirements — be a thinking partner, not an interviewer. Start open.
   - "What problem are you solving?"
   - "Who is the user and what's their pain?"
   - "What does success look like?"
2. Challenge vagueness. Never accept fuzzy answers. Make the abstract concrete.
3. Capture user stories with priorities: **P1 = MVP**, P2 = should have, P3 = nice to have
4. Write acceptance criteria in **WHEN/THEN/SHALL** format
5. Assign Requirement IDs: `[CATEGORY]-[NUMBER]` (e.g., `AUTH-01`, `CART-03`)
6. Write or update `.specs/features/[slug]/spec.md`

**Output:** `.specs/features/[feature-slug]/spec.md`

---

## Phase 2 — DESIGN (skip for Small/Medium)

**Goal:** Define HOW to build it — architecture, components, data model, API contract.

**Process:**
1. Read `spec.md`
2. Map requirement IDs to components
3. Define data model changes (new tables, modified schemas)
4. Define API contract (endpoints, request/response shapes)
5. Identify reusable code from codebase
6. Document open questions

**Output:** `.specs/features/[feature-slug]/design.md`

---

## Phase 3 — TASKS (skip when ≤3 obvious steps)

**Goal:** Break into GRANULAR, ATOMIC tasks. Clear dependencies. Parallel plan.

**One task = ONE of:**
- One component
- One function
- One API endpoint
- One file change

**Rules:**
- Every task has: What, Where, Depends on, Reuses, Requirement ID, Done when (testable), Tests, Gate
- Co-locate tests: tasks that create code with a required test type MUST include writing those tests
- Mark parallel tasks with `[P]` — they can run concurrently
- Use Conventional Commits format for each task's commit

**Output:** `.specs/features/[feature-slug]/tasks.md`

---

## Phase 4 — EXECUTE

**Goal:** Implement ONE task at a time. Surgical changes. Verify. Commit. Repeat.

**For every task, follow this cycle:**

1. **State** — Assumptions, files to touch, success criteria (MANDATORY before coding)
2. **RED** — Write tests FIRST (if task requires tests). Confirm they FAIL.
3. **GREEN** — Write minimum code to pass tests. Do NOT modify tests.
4. **VERIFY** — Run the gate check command from `TESTING.md`. Non-zero exit = STOP and fix.
5. **POST-GATE** — Verify test count, add `SPEC_DEVIATION` markers if implementation diverged
6. **COMMIT** — One atomic commit per task using Conventional Commits
7. **GUARDRAIL** — Do NOT act on unrelated improvements. Log them in `STATE.md` as deferred ideas.
8. **UPDATE** — Mark task done in `tasks.md`, update requirement traceability in `spec.md`

**Gate levels:**
| Level | Command | When |
|-------|---------|------|
| quick | unit tests | Unit-only tasks |
| full | unit + integration + e2e | E2E/integration tasks |
| build | build + lint + all tests | Last task in a phase |

---

## Quick Mode (≤3 files, one-sentence scope)

For bug fixes, config changes, small tweaks:

1. Create `.specs/quick/[NNN]-[slug]/TASK.md`
2. Implement directly
3. Verify (run gate check)
4. Commit
5. Write `.specs/quick/[NNN]-[slug]/SUMMARY.md`

---

## Commit Format (Conventional Commits 1.0.0)

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `style`, `perf`, `build`, `ci`, `chore`

Rules:
- Imperative mood ("add", not "added")
- Lowercase first letter, no period
- One task = one commit
- Include tests in the same commit as the code they test

---

## STATE.md — Persistent Memory

Update `STATE.md` every session. It tracks:
- **Current focus** — active feature, last task, next task, blockers
- **Decisions** — architectural decisions with rationale
- **Blockers** — issues preventing progress
- **Lessons learned** — what went wrong and what to do differently
- **Deferred ideas** — good ideas captured during implementation, out of current scope
- **Todos** — short-term tasks not tied to a feature spec

Always update before pausing or ending a session.

---

## Knowledge Verification Chain

When researching or making any technical decision, follow this chain in order:

```
Step 1: Codebase → check existing code, conventions, patterns in use
Step 2: Project docs → README, docs/, .specs/codebase/
Step 3: Library docs → query for current API/patterns
Step 4: Web search → official docs, reputable sources
Step 5: Flag as uncertain → "I'm not certain about X — here's my reasoning, but verify"
```

**NEVER assume or fabricate.** Uncertainty is always preferable to fabrication.

---

## Coding Principles

- Write the **simplest code that works** — no gold-plating
- **Touch ONLY the files listed in the task** — no scope creep
- **Reuse existing patterns** from `CONVENTIONS.md` — don't reinvent
- **One concern per function/component** — single responsibility
- **No `any` in TypeScript** — use `unknown` + type guards
- **No hardcoded secrets** — environment variables only
- **No `console.log` in production code** — use structured logger
- If you notice something that should be improved but is out of scope: **log it in STATE.md as a deferred idea**, do NOT act on it

---

## Session Start Checklist

When starting a new session:
1. Load `STATE.md` — check current focus, blockers, todos
2. Load `PROJECT.md` — confirm project context
3. If continuing a feature: load the relevant `spec.md`, `design.md`, `tasks.md`
4. Ask: "Where did we leave off?" if STATE.md current focus is set

## Session End Checklist

Before pausing or ending:
1. Update `STATE.md` — current focus, last task completed, next task, any new decisions/blockers/lessons
2. Mark completed tasks in `tasks.md`
3. Commit any uncommitted work

---

## Trigger Phrases

**Project-level:**

| When user says... | Do this |
|------------------|---------|
| "initialize project" / "setup project" | Create PROJECT.md + ROADMAP.md |
| "create roadmap" / "plan features" | Create or update ROADMAP.md |
| "map codebase" / "analyze existing code" | Populate all 7 `.specs/codebase/` docs |
| "document concerns" / "find tech debt" / "what's risky" | Populate CONCERNS.md |
| "record decision" / "log blocker" / "add todo" | Update STATE.md |
| "pause work" / "end session" | Update STATE.md, create session summary |
| "resume work" / "continue" | Load STATE.md, continue from last task |

**Feature-level (auto-sized):**

| When user says... | Do this |
|------------------|---------|
| "specify feature" / "define requirements" | Run Specify phase → write spec.md |
| "discuss feature" / "capture context" / "how should this work" | Run Discuss → write context.md |
| "design feature" / "architecture" | Run Design phase → write design.md |
| "break into tasks" / "create tasks" | Run Tasks phase → write tasks.md |
| "implement task" / "build" / "execute" | Run Execute phase |
| "validate" / "verify" / "test" / "UAT" / "walk me through it" | Run Validate phase |
| "quick fix" / "quick task" / "small change" / "bug fix" | Run Quick mode |
