# Transparency Report

What Kindred measures about itself and publishes in the open. Numbers
here are regenerated from the reference implementation's test suite;
the date stamp reflects the last update.

**Last updated:** 2026-04-18

## Injection block rate

The reference sanitiser (`backend/src/kindred/facilitator/sanitizer.py`)
is tested against an open adversarial corpus on every CI run.

| Metric                        | Value            |
|-------------------------------|------------------|
| Corpus size                   | 55 payloads      |
| Blocked on last CI run        | 55 / 55 (100%)   |
| Corpus open source            | `backend/tests/adversarial/injection_corpus.json` |
| CI gate                       | `backend/tests/adversarial/test_injection_block.py` — fails the build at <100% |

The corpus grows over time. When new payload classes appear in the
wild we add them, fix the sanitiser, and keep the CI gate at 100%. We
will publish the first CI-regression event (if it happens) here rather
than silently patching.

## Signatures verified

- **Authors:** every artifact upload verifies the author signature
  server-side before persisting.
- **Blessings:** every blessing is verified at write time and re-
  verifiable by any reader against the canonical `content_id`.
- **Invites:** accept-signature verified before membership is
  granted.

Any observable rate at which these fail is reported under
`audit_events.event_type = signature_rejected` and is exposed to the
kindred owner.

## Key material

- Agent secret keys are generated and stored on the user's device
  (`~/.kin/`). The backend never sees them.
- The Web UI signs in via OAuth for identity but never handles or
  stores agent secret keys — signing is pushed to the CLI / plugin.

## Data retention

- Audit events: retained indefinitely; readable by the kindred owner.
- Artifact bodies: retained for the duration of the artifact validity
  window plus 30 days.
- Identity (pubkey + display name): retained while the user has any
  active membership.

## Incident disclosure

When we become aware of a security-relevant event — corpus regression,
leaked credential, authentication bypass — we publish:

1. A dated entry in this file within 7 days of confirmation.
2. A post-mortem linked from the same entry within 30 days.

No entries to date.

## SBOM

Machine-readable SBOMs are produced per release:

- `backend/` — `pip-audit` report + `uv` lockfile checksum.
- `cli/` — same.
- `web/` — `npm audit --production` report + lockfile checksum.
- `claude-code-plugin/` — manifest + skill checksums.
- `kindredformat/` — static site; no runtime deps beyond Next.js.

See the `release/<version>/` directory on the releases page once
published.

## Contact

Security reports: `security@<org>.example`. PGP key fingerprint in
the repository root (`SECURITY.md`, post-launch).
