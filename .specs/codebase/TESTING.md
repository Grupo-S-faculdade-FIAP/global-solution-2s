# Testing

**Project:** [Project Name]
**Mapped on:** [YYYY-MM-DD]

---

## Test Framework

| Layer | Framework | Config |
|-------|-----------|--------|
| Unit | [e.g., Vitest] | `vitest.config.ts` |
| Integration | [e.g., Vitest + Supertest] | `vitest.config.ts` |
| E2E | [e.g., Playwright] | `playwright.config.ts` |

---

## Gate Check Commands

These are the MANDATORY gate commands used during Execute phase.
Every task specifies a gate level — the agent runs the corresponding command.

| Gate Level | Command | When to use |
|------------|---------|-------------|
| **quick** | `[e.g., pnpm test:unit]` | Unit tests only |
| **full** | `[e.g., pnpm test]` | Unit + integration + e2e |
| **build** | `[e.g., pnpm build && pnpm test]` | Build + all tests (last task in phase) |

---

## Test Coverage Matrix

Maps each code layer to its required test type.
Agents use this to assign the `Tests` field in tasks.

| Code Layer | Required Test Type | Notes |
|------------|--------------------|-------|
| React components | unit | Render + interaction tests |
| API routes / controllers | integration | Full request/response cycle |
| Services (business logic) | unit | Pure function tests |
| Repositories (DB access) | integration | With test DB |
| Utility functions | unit | |
| Configuration / env | none | Validated at startup |
| Type definitions | none | Compile-time only |
| E2E user flows | e2e | Critical paths only |

---

## Parallelism Assessment

Determines which test types are safe to run in parallel (affects `[P]` task flags).

| Test Type | Parallel-Safe | Reason |
|-----------|:------------:|--------|
| unit | ✅ Yes | No shared state |
| integration | ❌ No | Shares DB state |
| e2e | ❌ No | Shares browser/server state |

---

## Test Patterns

### Unit Test Pattern

```typescript
import { describe, it, expect } from 'vitest'
import { [functionUnderTest] } from './[module]'

describe('[module]', () => {
  it('[should do X when Y]', () => {
    // Arrange
    const input = [...]

    // Act
    const result = [functionUnderTest](input)

    // Assert
    expect(result).toEqual([expected])
  })
})
```

### Integration Test Pattern

```typescript
// [Show the pattern used in this project for integration tests]
```

### E2E Test Pattern

```typescript
// [Show the pattern used in this project for e2e tests with Playwright or similar]
```

---

## Coverage Goals

| Type | Target | Current |
|------|--------|---------|
| Unit | [e.g., 80%] | [track manually] |
| Integration | [e.g., critical paths] | [track manually] |
| E2E | [e.g., happy paths] | [track manually] |

---

## Running Tests

```bash
# Unit tests
[command]

# Unit tests with watch
[command]

# Integration tests
[command]

# E2E tests (headless)
[command]

# E2E tests (headed / debug)
[command]

# All tests
[command]

# Coverage report
[command]
```
