# [Feature Name] Tasks

**Feature:** `[feature-slug]`
**Design:** `.specs/features/[feature-slug]/design.md`
**Created:** [YYYY-MM-DD]
**Status:** Draft | Approved | In Progress | Done

---

## Execution Plan

### Phase 1: Foundation (Sequential)

Tasks that must be done first, in order.

```
T1 → T2 → T3
```

### Phase 2: Core Implementation (Parallel OK)

After foundation, these can run in parallel.

```
         ┌→ T4 ─┐
T3 ──────┼→ T5 ─┼──→ T7
         └→ T6 ─┘
```

### Phase 3: Integration (Sequential)

Bringing it all together.

```
T7 → T8
```

---

## Task Breakdown

### T1: [Task Title]

**What:** [One sentence: exact deliverable]
**Where:** `src/path/to/file.ts`
**Depends on:** None
**Reuses:** `src/existing/[Reference].ts`
**Requirement:** [FEAT]-01

**Done when:**

- [ ] [Specific, testable outcome]
- [ ] [Specific, testable outcome]
- [ ] Gate check passes: `[gate command]`
- [ ] Test count: [N] tests pass (no silent deletions)

**Tests:** unit | integration | e2e | none
**Gate:** quick | full | build

---

### T2: [Task Title]

**What:** [Exact deliverable]
**Where:** `src/path/to/file.ts`
**Depends on:** T1
**Reuses:** [existing pattern/file]
**Requirement:** [FEAT]-01

**Done when:**

- [ ] [Specific, testable outcome]
- [ ] [Specific, testable outcome]
- [ ] Gate check passes: `[gate command]`
- [ ] Test count: [N] tests pass

**Tests:** unit
**Gate:** quick

**Commit:** `feat([scope]): [description]`

---

### T3: [Task Title] [P]

> [P] = can run in parallel with other [P] tasks in same phase

**What:** [Exact deliverable]
**Where:** `src/path/to/file.ts`
**Depends on:** T2
**Reuses:** [existing pattern/file]
**Requirement:** [FEAT]-02

**Done when:**

- [ ] [Specific, testable outcome]
- [ ] Gate check passes: `[gate command]`
- [ ] Test count: [N] tests pass

**Tests:** unit
**Gate:** quick

---

## Granularity Check

| Task | Scope | Status |
|------|-------|:------:|
| T1: [name] | 1 [component/function/endpoint] | ✅ |
| T2: [name] | 1 [component/function/endpoint] | ✅ |
| T3: [name] | 1 [component/function/endpoint] | ✅ |

---

## Requirement Traceability

| Requirement ID | Covered by Tasks | Status |
|----------------|-----------------|--------|
| [FEAT]-01 | T1, T2 | Pending |
| [FEAT]-02 | T3 | Pending |
