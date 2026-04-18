# Kindred Web UI — Implementation Plan (06/07)

**Goal:** Livrează un Web UI Next.js 15 minimal care rezolvă P0 flows: invite landing, OAuth/passkey signup, dashboard cu kindreds, kindred view cu artifacte + blessing + audit + rollback. Dark-mode default, grimoire aesthetic minimalist, CSP-strict, XSS-proof pe artifact content.

**Architecture:** Next.js 15 App Router + React Server Components. Auth.js pentru OAuth (GitHub + Google) + WebAuthn (passkey). Backend proxy prin API routes care apelează FastAPI-ul Plan 01-02. Clientul primește doar date minime (no secret keys). Keypair-urile user-ului se pot genera client-side cu WebCrypto (SubtleCrypto Ed25519), cifrate cu passkey, stocate cript-at-rest. Pentru simplitate v0: server-side keystore protejat de session token — sacrifică self-custody pentru UX (tradeoff documented).

**Adversarial considerations implemented:**
- Invite link hijacking → one-time tokens (deja în Plan 01), no stateless preview exposing content
- XSS → DOMPurify + CSP nonce-based + no raw HTML in artifacts
- Session fixation → httpOnly + SameSite=Strict cookies + rotate on login
- Open redirect → strict whitelist in OAuth callback
- Privilege confusion → server-side authz checks, UI is suggestion-layer not gate
- Enumeration → 404 response shape identical for exists/not-exists (when unauth'd)
- Phishing clone → register kindred.sh + kindred.dev + docs.kindred.sh only; SRI on CDN assets

**Spec reference:** §6 Onboarding Protocol (link is the install), §4.1 Identity (OAuth/passkey), §9 MVP (Web UI minimal list).

---

## File Structure

```
web/
├── package.json
├── next.config.mjs
├── tailwind.config.ts
├── tsconfig.json
├── .env.local.example
├── src/
│   ├── app/
│   │   ├── layout.tsx                  # Root layout (dark-mode, fonts, CSP headers)
│   │   ├── page.tsx                    # Landing (public, minimal)
│   │   ├── api/auth/[...nextauth]/route.ts  # Auth.js route
│   │   ├── api/backend/[...path]/route.ts   # Proxy to FastAPI
│   │   ├── k/[slug]/page.tsx           # Invite landing (public preview + install CTAs)
│   │   ├── dashboard/
│   │   │   ├── page.tsx                # My kindreds
│   │   │   └── [slug]/
│   │   │       ├── page.tsx            # Kindred view
│   │   │       ├── artifacts/page.tsx
│   │   │       ├── audit/page.tsx
│   │   │       └── rollback/page.tsx
│   │   └── login/page.tsx              # OAuth + passkey entry
│   ├── components/
│   │   ├── ui/                         # shadcn/ui primitives (Button, Card, Badge, etc)
│   │   ├── provenance-chip.tsx         # Trust badge display
│   │   ├── artifact-card.tsx           # Renders KAF artifact safely
│   │   ├── install-ctas.tsx            # Per-harness install buttons
│   │   └── kindred-list.tsx
│   ├── lib/
│   │   ├── backend.ts                  # Typed fetch wrapper to FastAPI
│   │   ├── auth.ts                     # Auth.js config
│   │   ├── sanitize.ts                 # DOMPurify + marked wrapper
│   │   ├── csp.ts                      # CSP nonce generator
│   │   └── session.ts                  # Server-side session helpers
│   └── styles/
│       └── globals.css                 # Tailwind base + grimoire theme vars
└── tests/
    ├── unit/sanitize.test.ts
    ├── unit/provenance-chip.test.tsx
    ├── unit/artifact-card.test.tsx
    └── e2e/
        └── invite-flow.spec.ts         # Playwright — click invite → install CTA shown
```

---

## Task 1: Next.js bootstrap + Tailwind + shadcn/ui + grimoire theme

**Files:** `web/package.json`, `web/next.config.mjs`, `web/tailwind.config.ts`, `web/tsconfig.json`, `web/src/app/layout.tsx`, `web/src/app/page.tsx`, `web/src/styles/globals.css`, `web/.env.local.example`

- [ ] Bootstrap with `pnpm create next-app@latest web --typescript --tailwind --app --no-src-dir` (or manual)
  - Actually use `src/` layout. Manual: `pnpm init`, install deps.
- [ ] Dependencies:
  ```
  next@^15 react@^19 react-dom@^19
  tailwindcss@^3.4 autoprefixer@^10.4 postcss@^8.4
  @radix-ui/react-* (for shadcn/ui primitives: button, card, dialog, dropdown-menu, tabs, badge)
  class-variance-authority clsx tailwind-merge
  lucide-react
  next-auth@^5 @auth/core
  isomorphic-dompurify marked
  zod
  ```
- [ ] Dev deps: `@types/node @types/react @types/react-dom eslint eslint-config-next @typescript-eslint/* vitest @testing-library/react @testing-library/jest-dom jsdom playwright`
- [ ] Tailwind config with grimoire theme variables:
  ```ts
  // tailwind.config.ts
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        accent: 'hsl(var(--accent))',
        muted: 'hsl(var(--muted))',
        border: 'hsl(var(--border))',
        // trust tiers
        'tier-blessed': 'hsl(var(--tier-blessed))',
        'tier-peer': 'hsl(var(--tier-peer))',
      },
      fontFamily: {
        serif: ['Spectral', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  }
  ```
- [ ] `globals.css` with dark-mode-first variables:
  ```css
  :root {
    --background: 24 14% 6%;       /* Deep near-black with warm tint */
    --foreground: 40 15% 92%;      /* Warm off-white */
    --accent: 28 80% 58%;          /* Ember — warm, not blue */
    --muted: 24 8% 16%;
    --border: 24 8% 22%;
    --tier-blessed: 150 50% 50%;   /* Verdant */
    --tier-peer: 45 70% 55%;       /* Amber — cautious */
  }
  ```
- [ ] Landing page `app/page.tsx`:
  - Hero: tagline "Your agent now knows what your kindred knows." (serif large)
  - Subtitle: "A knowledge co-op for you and your friends' AI agents."
  - 3 feature cards: Signed artifacts, Private by default, Cross-vendor
  - CTA: "Create a kindred" (login-gated)
  - Footer: links to spec, moltformat.org (placeholder)
- [ ] Test: render landing, check tagline present, check no analytics scripts loaded
- [ ] Commit: `feat(web): Next.js 15 bootstrap + grimoire theme + landing`

---

## Task 2: Backend proxy + typed fetch wrapper

**Files:** `web/src/app/api/backend/[...path]/route.ts`, `web/src/lib/backend.ts`

- [ ] `app/api/backend/[...path]/route.ts`:
  - GET/POST/PUT/DELETE handler
  - Reads server session, extracts owner pubkey (stored in session)
  - Forwards request to `process.env.KINDRED_BACKEND_URL` with `x-owner-pubkey` or `x-agent-pubkey` header as appropriate
  - Streams response back (JSON only)
  - Strips server errors into `{error, message}` shape
- [ ] `lib/backend.ts`:
  - Typed client: `backend.kindreds.list()`, `backend.kindreds.create(...)`, `backend.artifacts.list(slug)`, `backend.artifacts.bless(slug, cid, sig)`, etc.
  - Uses native fetch, proxied through `/api/backend/*`
- [ ] Tests: mock global fetch, assert proxy shape + header passthrough
- [ ] Commit: `feat(web): backend proxy + typed fetch client`

---

## Task 3: Auth.js setup with OAuth (GitHub/Google) + passkey

**Files:** `web/src/app/api/auth/[...nextauth]/route.ts`, `web/src/lib/auth.ts`, `web/src/app/login/page.tsx`

- [ ] `lib/auth.ts`:
  - `NextAuth({ providers: [GitHub, Google, Passkey (WebAuthn)], adapter: ... })`
  - Session strategy: `jwt` with httpOnly+SameSite=Strict
  - On first login: derive owner pubkey client-side via WebCrypto Ed25519 OR generate server-side and store encrypted (tradeoff doc'd)
  - Callback: POST to backend `/v1/users` to register if missing
- [ ] Login page with 3 buttons: GitHub / Google / Passkey
- [ ] Env vars: `GITHUB_ID`, `GITHUB_SECRET`, `GOOGLE_ID`, `GOOGLE_SECRET`, `NEXTAUTH_SECRET`, `KINDRED_BACKEND_URL`
- [ ] Commit: `feat(web): Auth.js with OAuth + passkey`

**Note on keypair management:** For v0, server generates + stores encrypted with user-derived key (session password or passkey challenge). This trades self-custody for UX simplicity. Plan 07 follow-up: migrate to client-side WebCrypto + encrypted local storage + passkey unlock.

---

## Task 4: Invite landing page (public preview)

**Files:** `web/src/app/k/[slug]/page.tsx`, `web/src/components/install-ctas.tsx`

- [ ] Server component fetches `GET /v1/kindreds/{slug}` (public read) via backend proxy
  - On 404: generic "Invite not found or expired" page (no enumeration leak)
- [ ] Displays: kindred name, display_name, description, member count (if public), install CTAs per harness:
  - Claude Code: copy one-liner `curl kindred.sh/install | sh -s -- join <token>`
  - Cursor: (skip — user doesn't use)
  - ChatGPT: "Coming soon" placeholder
  - CLI: `pip install kindred-client && kin join <invite_url>`
- [ ] Install CTAs component uses clipboard API with success feedback
- [ ] Tests: render with mock kindred data, assert slug + name + CTAs
- [ ] Commit: `feat(web): invite landing page with per-harness install CTAs`

---

## Task 5: Dashboard + kindred list

**Files:** `web/src/app/dashboard/page.tsx`, `web/src/components/kindred-list.tsx`

- [ ] Server-guarded (redirect to /login if no session)
- [ ] Fetch user's kindreds from backend (using local cache of slugs in session OR add backend `GET /v1/users/{id}/kindreds` endpoint — minor Plan 01 extension)
- [ ] Layout: header (user avatar, logout) + KindredList (grid of cards) + "Create kindred" button
- [ ] KindredList card shows: slug, display_name, #members, #artifacts (fetched async)
- [ ] Commit: `feat(web): dashboard with kindred list`

---

## Task 6: Kindred view (artifacts list + tier badges + search)

**Files:** `web/src/app/dashboard/[slug]/page.tsx`, `web/src/components/artifact-card.tsx`, `web/src/components/provenance-chip.tsx`, `web/src/lib/sanitize.ts`

- [ ] `lib/sanitize.ts`: `safeMarkdown(content: string) -> HTML` via marked + DOMPurify
- [ ] `ProvenanceChip`: displays tier badge, author (truncated), outcome stats
- [ ] `ArtifactCard`: type icon, logical_name, valid_until, content preview (sanitized markdown), bless button (if not yet blessed by current user), provenance chip
- [ ] Kindred page: tabs {Artifacts, Audit, Rollback}. Default = Artifacts tab with search bar (client-side filter on logical_name + tags)
- [ ] Tests: render artifact card with untrusted content (XSS payload) → assert script tags stripped
- [ ] Commit: `feat(web): kindred view with safe artifact rendering`

---

## Task 7: Bless + propose (authenticated actions)

**Files:** extension to `artifact-card.tsx`, new API route for signing

- [ ] Bless flow:
  1. User clicks "Bless" on an artifact card
  2. Modal confirms: "You're signing this artifact's content_id. Proceed?"
  3. Client requests signing from server (server has agent keypair) OR client-side WebCrypto if we went self-custody — for v0 go server-side
  4. POST to backend `/v1/kindreds/{slug}/artifacts/{cid}/bless` with agent sig
  5. Refresh page; tier may flip to class-blessed
- [ ] Propose flow (less critical for v0): "Create artifact" button → modal with type dropdown + markdown editor → POST contribute
- [ ] Tests: mock backend, verify bless flow calls correct endpoint
- [ ] Commit: `feat(web): bless + propose artifact actions`

---

## Task 8: Audit log view + Rollback UI

**Files:** `web/src/app/dashboard/[slug]/audit/page.tsx`, `web/src/app/dashboard/[slug]/rollback/page.tsx`

- [ ] Audit: timeline of events (ordered by seq desc), each with ts, action, agent, payload summary
- [ ] Rollback: timeline with "Revert to this point" button (confirmation modal with warning)
- [ ] Commit: `feat(web): audit log + rollback UI`

---

## Task 9: CSP + security headers

**Files:** `web/next.config.mjs`, `web/middleware.ts`

- [ ] Next.js middleware sets headers:
  ```
  Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-<nonce>'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' ${BACKEND_URL}; frame-ancestors 'none';
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
  ```
- [ ] Nonce generated per request, passed to scripts via headers.get
- [ ] Test: curl landing page, assert CSP header present + strict
- [ ] Commit: `feat(web): strict CSP + security headers`

---

## Task 10: E2E Playwright test

**Files:** `web/playwright.config.ts`, `web/tests/e2e/invite-flow.spec.ts`

- [ ] Launch Next.js dev server + backend (docker-compose), navigate to `/k/<slug>?inv=<token>`, assert landing renders, click Install CTA, assert clipboard contains one-liner
- [ ] Mark as `@pytest.mark.slow` equivalent — skip by default in CI, opt-in via env var
- [ ] Commit: `test(web): Playwright invite-flow E2E`

---

## Task 11: Web CI workflow

**Files:** `.github/workflows/web-ci.yml`

- [ ] Lint (eslint), typecheck (tsc --noEmit), test (vitest), build (next build)
- [ ] Commit: `ci: Web GitHub Actions workflow`

---

## Success criteria

- Lighthouse score ≥90 perf/a11y/best-practices on landing page
- CSP strict, no inline scripts except nonce-based
- XSS test passes: malicious artifact content rendered safely
- Invite link → install CTA visible within 2 clicks
- Auth flow: OAuth or passkey login, kindred list visible in <3 clicks post-login
- All 20+ web tests pass
- Dark-mode-first, responsive (mobile via Tailwind responsive utilities)

---

## Concerns / deferred

- Self-custody keypair via client-side WebCrypto → Plan 07 follow-up
- Rich markdown editor for artifact propose → v0.5
- Cross-device passkey sync → relies on platform (Apple/Google passkey cloud)
- ChatGPT Custom GPT install → stub, full implementation v0.5
- i18n → en only for v0
- Analytics → none self-hosted in v0; add Umami post-launch if needed
