# [Feature Name] Specification

**Feature slug:** `[feature-slug]`
**Created:** [YYYY-MM-DD]
**Status:** Draft | Approved | In Design | In Tasks | Implementing | Done

---

## Problem Statement

[Describe the problem in 2-3 sentences. What pain point are we solving? Why now?]

---

## Goals

- [ ] [Primary goal with measurable outcome]
- [ ] [Secondary goal with measurable outcome]

---

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| [Feature X] | [Why excluded] |
| [Feature Y] | [Why excluded] |

---

## User Stories

### P1: [Story Title] ⭐ MVP

**User Story:** As a [role], I want [capability] so that [benefit].

**Why P1:** [Why this is critical for MVP]

**Acceptance Criteria:**

1. WHEN [user action/event] THEN system SHALL [expected behavior]
2. WHEN [user action/event] THEN system SHALL [expected behavior]
3. WHEN [edge case] THEN system SHALL [graceful handling]

**Independent Test:** [How to verify this story works alone — e.g., "Can demo by doing X and seeing Y"]

---

### P2: [Story Title]

**User Story:** As a [role], I want [capability] so that [benefit].

**Why P2:** [Why this isn't MVP but important]

**Acceptance Criteria:**

1. WHEN [event] THEN system SHALL [behavior]
2. WHEN [event] THEN system SHALL [behavior]

**Independent Test:** [How to verify]

---

### P3: [Story Title]

**User Story:** As a [role], I want [capability] so that [benefit].

**Why P3:** [Why this is nice-to-have]

**Acceptance Criteria:**

1. WHEN [event] THEN system SHALL [behavior]

---

## Edge Cases

- WHEN [boundary condition] THEN system SHALL [behavior]
- WHEN [error scenario] THEN system SHALL [graceful handling]
- WHEN [unexpected input] THEN system SHALL [validation response]

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story | Phase | Status |
|----------------|-------|-------|--------|
| [FEAT]-01 | P1: [Story] | Design | Pending |
| [FEAT]-02 | P1: [Story] | Design | Pending |
| [FEAT]-03 | P2: [Story] | — | Pending |

**ID format:** `[CATEGORY]-[NUMBER]` — e.g., `AUTH-01`, `CART-03`, `NOTIF-02`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** X total, Y mapped to tasks, Z unmapped ⚠️

---

## Success Criteria

How we know the feature is successful:

- [ ] [Measurable outcome — e.g., "User can complete X in < 2 minutes"]
- [ ] [Measurable outcome — e.g., "Zero errors in Y scenario"]
