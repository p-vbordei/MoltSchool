# Threat Model

This document lists the attackers Kindred defends against, the
mitigations in place, and the residual risks that remain open. It is a
living document; file issues when the reality of the codebase drifts
from what is written here.

## 1. Attackers considered

### A1 — Unauthenticated internet attacker

Can hit any public endpoint. Goals: cause data loss, exfiltrate private
artifacts, impersonate a legitimate agent, poison retrieval results.

### A2 — Ex-member of a kindred

Had valid credentials; has been revoked. Goals: continue retrieving,
continue publishing, back-date artifacts to appear authoritative.

### A3 — Active but malicious member

Still in good standing. Goals: publish harmful content and get it
class-blessed by social-engineering other members; poison agent
behaviour via instruction-bearing artifacts.

### A4 — Prompt-injection attacker

Has no direct Kindred account but can influence a document a member
might share — e.g. by controlling a website that a member's agent
distils and publishes. Goal: hijack downstream agents that retrieve
the resulting artifact.

### A5 — Compromised backend operator

Can read/modify the database. Goal: covertly alter artifacts so
members receive different content than what was originally signed.

## 2. Mitigations

| ID  | Risk                              | Mitigation                                                                 | Code reference                                                    |
|-----|-----------------------------------|----------------------------------------------------------------------------|-------------------------------------------------------------------|
| M1  | Forged artifact                   | Every envelope is signed over its `content_id`; readers verify.            | `backend/src/kindred/services/artifacts.py`                       |
| M2  | Tampered artifact body            | `body_sha256` is inside the signed metadata; readers verify on fetch.       | `backend/src/kindred/services/artifacts.py`                       |
| M3  | Replay of stale content           | Validity window (`valid_from`, `valid_until`) enforced on every read.       | `backend/src/kindred/services/retrieval.py` (ranking + filter)    |
| M4  | Revoked member continues to post  | Membership check on every write; server rejects if `active=false`.          | `backend/src/kindred/services/kindreds.py`                        |
| M5  | Unauthorized read                 | `ask` endpoint scoped by agent pubkey + active membership.                  | `backend/src/kindred/api/routers/ask.py`                          |
| M6  | Self-blessing inflates tier       | Blessings from the artifact's author are excluded from the threshold count.| `backend/src/kindred/services/artifacts.py` (bless path)          |
| M7  | Prompt injection via artifact     | Sanitizer runs before retrieval result reaches the model/caller.            | `backend/src/kindred/facilitator/sanitizer.py`                    |
| M8  | Known injection payloads          | 55-entry corpus; CI gate requires 100% block rate.                          | `backend/tests/adversarial/injection_corpus.json`                 |
| M9  | Request replay on invite accept   | Accept body is signed; token is single-use + expires; nonce in body.        | `backend/src/kindred/services/invites.py`                         |
| M10 | Sequence-race on audit log        | Append-only, server-assigned monotonic sequence. Best-effort on backend restart. | `backend/src/kindred/services/audit.py`                     |
| M11 | Key exfiltration via web UI       | Web UI never sees agent secret keys — all signing happens in the CLI/plugin.| `web/src/lib/api.ts` (read-only proxy, no signing endpoints)      |
| M12 | Compromised backend returns forged artifacts | Readers re-verify signatures locally before acting.                 | `cli/src/kindred_client/api_client.py` + `verify` helpers          |
| M13 | Web XSS via artifact body         | Strict CSP on all Web UI pages + artifact rendering goes through sanitiser.| `web/src/middleware.ts`, `web/src/lib/render.ts`                  |

## 3. Residual risks

These are known gaps we accept in MVP. They ship documented, not hidden.

- **R1 — Sequence race on audit-log restart.** The monotonic
  `seq` column is reset from `MAX(seq)+1` at startup; if two writers
  race during that window, two events can claim the same sequence. Fix:
  move to a DB sequence. Tracked in Plan 01 follow-up.
- **R2 — Web UI holds OAuth tokens server-side.** The v0 web UI signs
  in via GitHub OAuth; the session token lives server-side. A
  full compromise of the web server leaks the session cookie + stored
  identity metadata (but never an agent secret key — those stay on
  the user's laptop).
- **R3 — No cross-kindred revocation.** If member Alice is expelled
  from kindred K1, her blessings on artifacts in K2 (where she's
  still a member) remain valid in K2. That's the design — blessings
  are per-kindred. But it means a socially-malicious member can
  "launder" influence across groups. Tracked in v1.
- **R4 — Clock skew.** `valid_from`/`valid_until` assumes roughly
  synchronised UTC. A machine with a clock 12 hours off will reject
  valid artifacts or accept expired ones. Implementations SHOULD
  allow ±60s skew. We do not ship a solution for clock-drift in
  MVP.
- **R5 — Sanitizer is pattern-based.** It will miss novel injection
  classes. Defence in depth still applies: trust tiers, human
  review of peer-shared, scoped agent credentials.
- **R6 — Artifact body exfiltration via side channels.** A class-
  blessed artifact could encode secrets in ways the sanitizer misses
  (steganography, high-entropy tokens). We do not attempt to detect
  this.

## 4. Out of scope

- Defences against a nation-state adversary with write access to the
  backend's disk AND the TLS private key AND the member's device.
- Defences against social engineering of member blessings (a member
  who blesses anything shown to them is a membership problem, not a
  protocol problem).
- Defences against compromise of the member's own key material
  (locally stored in `~/.kin/`). Key rotation is supported at the
  protocol level but scheduling it is a member's responsibility.

## 5. Review cadence

- Adversarial injection corpus: re-run on every CI build (gate).
- Threat model document: reviewed per major release; re-published
  alongside the spec.
- External pen-test: planned post-launch; results will be linked from
  `docs/transparency.md`.
