# Kindred Web UI

Next.js 15 (App Router + RSC) frontend for Kindred. Dark-mode-first
grimoire theme, strict CSP, DOMPurify-equivalent markdown sanitization.

## Stack

- **Next.js 15** with React 19 RC, App Router, React Server Components
- **Tailwind CSS 3.4** with CSS variables for the grimoire palette
- **Auth.js v5** (NextAuth) — GitHub OAuth live; Google + Passkey stubbed
- **sanitize-html + marked** for safe artifact markdown
- **Vitest + @testing-library/react** for unit tests
- **Playwright** for a single happy-path e2e

## Dev

```bash
cd web
nvm use            # or ensure Node 20+
npm install
cp .env.local.example .env.local
# fill in GITHUB_ID, GITHUB_SECRET, NEXTAUTH_SECRET
npm run dev
```

## Scripts

| Command              | What                                         |
| -------------------- | -------------------------------------------- |
| `npm run dev`        | Dev server on http://localhost:3000          |
| `npm run build`      | Production build                             |
| `npm run start`      | Start built server                           |
| `npm run lint`       | ESLint                                        |
| `npm run typecheck`  | `tsc --noEmit`                                |
| `npm run test`       | Vitest unit suite                            |
| `npm run test:e2e`   | Playwright (needs `npx playwright install`)   |

## Architecture

- **/api/auth/[...nextauth]** — Auth.js route
- **/api/backend/[...path]** — proxy to `KINDRED_BACKEND_URL` with session-
  bound pubkey headers; sanitizes upstream errors
- **src/lib/backend.ts** — typed client used by both RSC and client components
- **src/lib/sanitize.ts** — `safeMarkdown(s)` pipeline
- **src/middleware.ts** — per-request CSP nonce + strict security headers

## v0 tradeoffs (Plan 07 will revisit)

### Keystore is server-side

Owner + agent Ed25519 keypairs are (intended to be) minted on first login and
encrypted at rest with `NEXTAUTH_SECRET`. This means the server can
technically impersonate you, which is **not self-custody**. We made this
tradeoff for single-click onboarding; Plan 07 migrates to client-side
WebCrypto + passkey-wrapped keys so the private half never leaves your
browser.

In this v0 commit the JWT callback stubs pubkeys from the OAuth subject.
Real Ed25519 generation + encrypted persistence is the first follow-up.

### Only GitHub OAuth is live

Google and Passkey login are disabled placeholder buttons. Passkey in
particular requires a WebAuthn challenge/response round-trip that we
haven't wired — Plan 07.

### Bless is server-signed

Bless currently posts `sig: "server-side-v0"` to the backend; the backend
signs on behalf of the agent with the stored key. Plan 07 moves to
client-side WebCrypto signing.

### Rollback UI is read-only

You can see rollback points but the "Revert to here" button is disabled
pending the Plan 07 confirmation-flow polish. The backend endpoint exists.

## Security notes

- Strict CSP with per-request nonce, `strict-dynamic`, `frame-ancestors
  'none'`, `object-src 'none'`, narrow `connect-src` whitelist
- `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, HSTS preload
- DOMPurify-equivalent allow-list sanitizer for artifact markdown (XSS
  suite covers `<script>`, `javascript:` URLs, inline handlers, iframes,
  embeds, SVG)
- Session cookie is httpOnly + SameSite=Strict
- Invite landing returns generic 404 on missing/expired to prevent
  enumeration
