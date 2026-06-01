# Concerns

**Project:** [Project Name]
**Mapped on:** [YYYY-MM-DD]

> ⚠️ Load this file BEFORE planning features that touch flagged areas, estimating risk, or modifying fragile components.

---

## Fragile Areas

Components/modules where changes carry high risk of regressions.

| Area | File(s) | Risk | Why fragile | Mitigation |
|------|---------|:----:|------------|------------|
| [e.g., Auth middleware] | `src/middleware.ts` | 🔴 High | Touches all routes | Test all auth flows before deploying |
| [e.g., Payment flow] | `src/services/payment.ts` | 🔴 High | Handles real money | Never modify without full e2e run |
| [e.g., DB migrations] | `prisma/migrations/` | 🟡 Medium | Irreversible | Always backup + test in staging |

---

## Technical Debt

Known shortcuts, TODO items, and legacy patterns that should be addressed eventually.

| ID | Description | Location | Impact | Priority |
|----|-------------|---------|--------|----------|
| TD-001 | [e.g., Missing input validation on admin routes] | `src/app/admin/` | Security risk | High |
| TD-002 | [e.g., N+1 queries in product listing] | `src/services/product.ts` | Performance | Medium |
| TD-003 | [e.g., Hardcoded pagination limit] | `src/repositories/user.ts` | Scalability | Low |

---

## Security Concerns

| Concern | Area | Status | Notes |
|---------|------|--------|-------|
| Input sanitization | API routes | ✅ Done | Using Zod schemas |
| CSRF protection | Form submissions | 🟡 Partial | Check on new forms |
| Rate limiting | Auth endpoints | ❌ Missing | Add before v1 launch |
| Secrets in env | All integrations | ✅ Done | `.env.local` git-ignored |

---

## Performance Concerns

| Concern | Area | Status | Notes |
|---------|------|--------|-------|
| [e.g., Large bundle size] | `src/app/` | 🟡 Watch | Monitor with `pnpm analyze` |
| [e.g., Unoptimized images] | `public/` | ✅ Fixed | Using next/image |

---

## Rules for Fragile Areas

When a task touches a flagged area, the agent MUST:

1. Note the risk level in the implementation plan
2. Use the **full** gate check (not quick) after changes
3. List the specific tests that cover the fragile area
4. Flag if no tests exist — do not proceed without adding them

---

<!-- Update this file whenever new tech debt is discovered or concerns are resolved. -->
