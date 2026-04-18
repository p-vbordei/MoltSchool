# Launch Checklist

Tickable gate for shipping Kindred 0.1. Every box below must be
checked before a public launch post goes live.

## Pre-launch — code & content

- [ ] All 7 plans merged to `main`.
- [ ] Backend CI green on `main` (`backend/.github/workflows/backend-ci.yml`).
- [ ] CLI CI green on `main`.
- [ ] Web CI green on `main`.
- [ ] Onboarding benchmark CI green (`<60s` on last run).
- [ ] Adversarial injection corpus: 100% block rate on last run.
- [ ] 5 seed grimoires populate cleanly via `scripts/seed_grimoires.py`.
- [ ] Integration smoke test passes on a clean checkout
      (`./scripts/integration_smoke.sh`).

## Pre-launch — docs

- [ ] Root `README.md` links to every component + plan.
- [ ] `docs/quick-start.md` reproducible by a new user in <5 min.
- [ ] `docs/threat-model.md` current — all mitigations cross-
      referenced to code paths that still exist.
- [ ] `docs/transparency.md` date-stamped within the last 7 days.
- [ ] KAF spec at `kindredformat/content/kaf-spec-0.1.md` matches the
      reference implementation byte-for-byte (test vectors pass).
- [ ] `kindredformat/` static site builds cleanly (`npm run build`).

## Pre-launch — infra

- [ ] `kindredformat.org` DNS + TLS configured.
- [ ] `kindredformat/` `out/` deployed to host.
- [ ] Backend hosted at the URL printed in quick start.
- [ ] Backend monitoring on: uptime, p95 request latency, DB
      connection count, disk usage.
- [ ] PagerDuty / on-call rotation defined for backend.
- [ ] Backups running (see `docs/seed-grimoires/postgres-ops/`).
- [ ] First PITR drill recorded.

## Pre-launch — invites & identity

- [ ] 200 invite tokens minted and stored securely.
- [ ] Allocation plan for invites: who gets batch 1, batch 2, batch
      3 over the first 14 days.
- [ ] Security contact email live (`security@<org>.example`).
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
- Server-side key signing removed from v0 web UI (move to browser-
  local WebCrypto).
- Webhook for repo references (KAF `repo_ref` v1 type).
- `conversation_distilled` and `benchmark_ref` KAF types.
- Cross-kindred revocation propagation (residual risk R3 in threat
  model).
- Audit-log sequence race fix (residual risk R1).
