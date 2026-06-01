# Structure

**Project:** [Project Name]
**Mapped on:** [YYYY-MM-DD]

---

## Directory Tree

```
[project-root]/
├── .specs/               # Spec-Driven documentation (this folder)
├── .github/              # GitHub config + Copilot instructions
├── .cursor/              # Cursor rules
├── src/
│   ├── app/              # [describe purpose]
│   ├── components/       # [describe purpose]
│   ├── services/         # [describe purpose]
│   ├── repositories/     # [describe purpose]
│   ├── hooks/            # [describe purpose]
│   ├── lib/              # [describe purpose]
│   ├── types/            # [describe purpose]
│   └── config/           # [describe purpose]
├── prisma/               # [if using Prisma]
│   └── schema.prisma
├── public/               # Static assets
├── tests/                # [integration / e2e tests location]
├── package.json
├── tsconfig.json
└── [other config files]
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/app/layout.tsx` | Root layout — global providers, metadata |
| `src/lib/db.ts` | Database client singleton |
| `src/config/env.ts` | Environment variable validation |
| `prisma/schema.prisma` | Database schema |
| `.env.local` | Local environment variables (git-ignored) |
| `.env.example` | Environment variables template |

---

## Module Aliases

Configured path aliases (from `tsconfig.json` or `vite.config.ts`):

| Alias | Resolves to |
|-------|------------|
| `@/*` | `src/*` |
| `@components/*` | `src/components/*` |
| `@services/*` | `src/services/*` |

---

## Test File Location Strategy

| Test type | Location |
|-----------|---------|
| Unit tests | Co-located — `[Component].test.ts(x)` next to source |
| Integration tests | `tests/integration/` |
| E2E tests | `tests/e2e/` |
