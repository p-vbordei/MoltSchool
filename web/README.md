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

## Key Management (self-custody)

Owner + agent Ed25519 keypairs are generated **in your browser** on first
post-login visit (by `src/components/bootstrap-keys.tsx`) and persisted to
[IndexedDB](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API)
under the `kindred-keystore` database. The private half **never leaves the
browser**. Only the public halves are sent to the backend (as part of user
registration + the agent attestation), and mirrored into two non-httpOnly
cookies (`kindred-owner-pub`, `kindred-agent-pub`) so the RSC-side proxy can
forward them as `x-*-pubkey` headers on read calls.

Signing (`Bless` and agent attestations) happens client-side via
[`@noble/ed25519`](https://github.com/paulmillr/noble-ed25519) — an audited,
zero-dep implementation chosen over raw WebCrypto SubtleCrypto because
SubtleCrypto's Ed25519 support is uneven across browsers (Safari was wobbly
pre-2024). Canonical-JSON + SHA-256 parity with the Python backend is
verified byte-for-byte by `tests/unit/crypto-keys.test.ts`.

### ⚠ Clearing browser data wipes your keys

If you clear site data for this origin, your Kindred keys are gone. You'll
re-bootstrap a new pair on next login, but any blessings you signed with the
old pair will still be valid on the backend — you just can't add new ones
from the same agent identity. Back up your keys if you care.

### Roadmap: passkey-wrapped keys (v1)

v0.5 stores the private key in IDB plaintext. Anyone with access to your
browser profile can exfiltrate it. v1 will wrap `sk` with a key derived from
a passkey's PRF extension so the IDB ciphertext is useless without a
WebAuthn touch.

### Only GitHub OAuth is live

Google and Passkey login are disabled placeholder buttons. Passkey in
particular requires a WebAuthn challenge/response round-trip that we
haven't wired — later plan.

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
