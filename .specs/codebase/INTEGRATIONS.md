# Integrations

**Project:** [Project Name]
**Mapped on:** [YYYY-MM-DD]

---

## External Services

| Service | SDK / Client | Auth Method | Purpose | Docs |
|---------|-------------|-------------|---------|------|
| [e.g., Stripe] | `stripe` | Secret key (env) | Payments | [link] |
| [e.g., SendGrid] | `@sendgrid/mail` | API key (env) | Email | [link] |
| [e.g., Cloudinary] | `cloudinary` | API key (env) | Media storage | [link] |
| [e.g., Clerk] | `@clerk/nextjs` | Publishable/secret keys (env) | Auth | [link] |

---

## Internal APIs

| API | Base URL (env var) | Auth | Notes |
|-----|-------------------|------|-------|
| [Service name] | `NEXT_PUBLIC_API_URL` | Bearer token | [notes] |

---

## Webhooks

| Provider | Endpoint | Events | Validation |
|----------|----------|--------|------------|
| [e.g., Stripe] | `/api/webhooks/stripe` | `payment_intent.succeeded` | Signature check |

---

## Environment Variables

All integrations use environment variables — never hardcoded keys.

| Variable | Required | Description | Where to get |
|----------|:--------:|-------------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string | DB provider |
| `NEXTAUTH_SECRET` | ✅ | Auth session secret | Generate: `openssl rand -base64 32` |
| `NEXTAUTH_URL` | ✅ | App base URL | `http://localhost:3000` in dev |
| `[INTEGRATION]_API_KEY` | ✅ | [Service] API key | [Service dashboard] |

> See `.env.example` for the full list.

---

## Integration Patterns

### Singleton Client

```typescript
// lib/stripe.ts — create client once, import everywhere
import Stripe from 'stripe'

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2024-06-20',
})
```

### Error Handling for External Calls

```typescript
// Always wrap external calls — never let provider errors propagate unhandled
try {
  const result = await externalService.doSomething()
  return result
} catch (error) {
  // Log + rethrow or transform to domain error
  throw new IntegrationError(`[ServiceName] failed: ${error.message}`)
}
```
