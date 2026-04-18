# Launch Checklist

Tickable gate for shipping Kindred 0.1. Every box below must be
checked before a public launch post goes live.

**Status snapshot (2026-04-18):** code and infra gates are green. Invite
pipeline + launch copy pending.

## Pre-launch — code & content

- [x] All shipping plans merged to `main` (01-04, 06, 07; Plan 05 / Cursor skipped per user direction).
- [x] Backend CI green on `main` (`.github/workflows/backend-ci.yml`).
- [x] CLI CI green on `main` (`.github/workflows/cli-ci.yml`).
- [x] Web CI green on `main` (`.github/workflows/web-ci.yml`).
- [x] Adversarial injection corpus: 100% block rate on last run (55/55).
- [x] 5 seed grimoires populate cleanly via `scripts/seed_grimoires.py`
      (verified against the live backend on 2026-04-18; all 15 artifacts
      uploaded).
- [x] Integration smoke test passes on a clean checkout
      (`./scripts/integration_smoke.sh`).
- [ ] Onboarding benchmark CI green (`<60s` on last run).

## Pre-launch — docs

- [x] Root `README.md` links to every component + plan.
- [x] `docs/quick-start.md` reproducible by a new user in <5 min (uses
      the live invite URL scheme; mint step included).
- [x] `docs/threat-model.md` current — all mitigations cross-
      referenced to code paths that still exist.
- [x] `docs/transparency.md` date-stamped within the last 7 days.
- [x] `docs/deployment.md` documents the Railway topology + seven
      failure modes we hit on first deploy.
- [x] KAF spec at `kindredformat/content/kaf-spec-0.1.md` matches the
      reference implementation byte-for-byte
      (`backend/tests/kaf/test_vectors.py` verifies 12 vectors).
- [x] `kindredformat/` static site builds cleanly (`npm run build`).

## Pre-launch — infra

- [x] Backend hosted and healthy at
      https://kindred-backend-production-4024.up.railway.app (`/healthz`
      returns 200).
- [x] Web UI hosted at https://kindred-web-production.up.railway.app.
- [x] KAF spec site hosted at https://kindredformat-production.up.railway.app.
- [x] Postgres managed by Railway plugin; auto-DATABASE_URL wired.
- [ ] `kindredformat.org` DNS + TLS configured (cutover pending — Railway
      has a valid cert on the `*.up.railway.app` subdomain).
- [ ] `kindred.sh` custom domain for the Web UI.
- [ ] Object storage migrated off `InMemoryObjectStore` to S3 / R2
      (artifact bodies are lost on each redeploy until this lands).
- [ ] Backend monitoring on: uptime, p95 request latency, DB
      connection count, disk usage.
- [ ] On-call rotation defined.
- [ ] First PITR drill recorded (Railway auto-backups exist; restore
      path not yet verified).

## Pre-launch — invites & identity

- [ ] 200 invite tokens minted and stored securely.
- [ ] Allocation plan for invites: who gets batch 1, batch 2, batch 3
      over the first 14 days.
- [ ] Real GitHub OAuth App registered (placeholders in
      `GITHUB_ID`/`GITHUB_SECRET` on `kindred-web` must be replaced
      before the Web UI sign-in path works).
- [ ] Security contact email live.
- [ ] `SECURITY.md` in the repo root with PGP fingerprint.

## Launch day

- [ ] HN post drafted and reviewed (copy lives in a separate
      `launch-copy.md`, not in this repo).
- [ ] Announcement blog post live at the project's blog.
- [ ] Social posts scheduled for T+0, T+6h, T+24h, T+72h.
- [ ] Weekly digest email infrastructure armed.
- [ ] Support inbox staffed for the first 48 hours.

## Post-launch — metric tracking

Daily for T+7 days, weekly for T+30 days:

- [ ] Signups → activated (joined a kindred) → first-ask conversion.
- [ ] p95 onboarding time (from benchmark CI + real-user).
- [ ] Injection corpus block rate (still 100%, if not: INCIDENT).
- [ ] Active kindreds count + artifacts-per-kindred distribution.
- [ ] Weekly-active-agents count.
- [ ] Cost per user per day (see LLM eval grimoire).

## T+30 decision

At T+30 days review against our go/pivot/kill thresholds:

- **Go:** ≥ 20 active kindreds, median weekly-active-agent count
  ≥ 5, onboarding p95 < 60s, zero unresolved SEV-1 security
  incidents.
- **Pivot:** any one gate missed but with a hypothesis for the fix.
  Document the hypothesis and re-review at T+60d.
- **Kill:** no recovery path; publish a post-mortem, release the
  reference code under a permissive licence, and move on.

Record the decision in a dated file under `docs/launch/` and link
it from the README.

## Follow-up (post-launch tasks already known)

Tracked as separate issues, not gated on launch:

- PyPI publish of `kindred-client`.
- Real GitHub App + Google OAuth client registration.
- Object storage migration from `InMemoryObjectStore` to S3 / Cloudflare R2.
- Passkey PRF wrapping of the client-side keystore (currently IDB
  plaintext; `@noble/ed25519` parity is already live).
- Custom-domain cutover to `kindred.sh` + `kindredformat.org`.
- Cleanup of 4 orphaned Postgres volumes left by early iteration
  (see `docs/deployment.md`).
- Rotate the admin Railway API token used during first deploy.

## Already landed (was on the v0 follow-up list, now done)

- [x] KAF v1 types: `repo_ref`, `conversation_distilled`, `benchmark_ref`.
- [x] Audit-log sequence race fix (SAVEPOINT retry on IntegrityError).
- [x] Web UI client-side WebCrypto signing with `@noble/ed25519`
      (owner + agent keypairs generated in-browser, stored in IDB,
      never sent server-side).
- [x] Byte-exact KAF test vectors for cross-language implementers
      (`backend/tests/kaf/vectors.json` — 6 vectors incl. `sig_v1`).
