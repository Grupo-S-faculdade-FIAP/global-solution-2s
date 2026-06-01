# Conventions

**Project:** [Project Name]
**Mapped on:** [YYYY-MM-DD]

> These are the coding conventions discovered in this codebase.
> Agents MUST follow these when generating or modifying code.

---

## Naming

| Entity | Convention | Example |
|--------|-----------|---------|
| Files (components) | PascalCase | `UserCard.tsx` |
| Files (utils/services) | camelCase | `authService.ts` |
| Files (routes/pages) | kebab-case | `user-profile/page.tsx` |
| Variables / functions | camelCase | `getUserById` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Types / Interfaces | PascalCase | `UserProfile`, `AuthState` |
| CSS classes | kebab-case | `user-card__avatar` |

---

## File Organization

```
src/
├── app/               # Next.js pages / routes
├── components/        # Reusable UI components
│   └── [Component]/
│       ├── index.tsx
│       └── [Component].test.tsx
├── services/          # Business logic
├── repositories/      # Data access layer
├── hooks/             # Custom React hooks
├── lib/               # Shared utilities
├── types/             # Global TypeScript types
└── config/            # App configuration
```

---

## Code Style

- **Formatter:** [e.g., Prettier — config in `.prettierrc`]
- **Linter:** [e.g., ESLint — config in `eslint.config.ts`]
- **Tab width:** [e.g., 2 spaces]
- **Quotes:** [e.g., single quotes]
- **Semicolons:** [e.g., required / omitted]
- **Trailing commas:** [e.g., all / none]

---

## Patterns

### Error Handling

```typescript
// Pattern used in this codebase:
// [describe or show the error handling pattern]
```

### API Responses

```typescript
// Standard response shape:
// { data: T | null, error: string | null }
```

### Async / Await

```typescript
// Use async/await, not .then()
// Wrap in try/catch at the service boundary
```

### Imports

```typescript
// Order: external libs → internal aliases → relative paths
import { useState } from 'react'
import { db } from '@/lib/db'
import { UserCard } from '../UserCard'
```

---

## Prohibited Patterns

- ❌ No `any` type in TypeScript — use `unknown` + type guards
- ❌ No direct DB queries in components or API routes — use services/repositories
- ❌ No hardcoded secrets — use environment variables
- ❌ No `console.log` in production code — use structured logger
- ❌ No inline styles — use Tailwind classes or CSS modules

---

## Git Conventions

**Commit format:** Conventional Commits 1.0.0

```
<type>(<scope>): <description>
```

| Type | When |
|------|------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change, no behavior change |
| `test` | Test additions/corrections |
| `docs` | Documentation only |
| `chore` | Maintenance, deps |
| `ci` | CI/CD changes |

**Branch naming:** `[type]/[short-description]` — e.g., `feat/user-auth`, `fix/cart-total`
