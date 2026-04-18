# Kindred Artifact Format (KAF) 0.1

**Status:** Draft — stable for MVP, may receive additive minor revisions.
**Publication date:** 2026-04-18
**Canonical URL:** https://kindredformat.org
**Reference implementation:** https://github.com/kindred/kindred

---

## Abstract

The Kindred Artifact Format (KAF) is a minimal portable envelope for agent-
shareable knowledge artifacts: CLAUDE.md files, routines (distilled
playbooks), skill references, repository references, distilled
conversations, and benchmark references. A KAF artifact carries a stable
cryptographic identity (`content_id`), one or more Ed25519 signatures, and a
small metadata header that lets verifiers derive trust tier, validity
window, and provenance without re-downloading the underlying body.

KAF is designed for small artifacts (typically <64 KiB body) that move
between agents through peer-to-peer channels, WebSocket digests, or HTTP
pulls, and that must remain verifiable even when the issuing server is
unavailable.

## 1. Conformance

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in RFC 2119 and RFC 8174 when,
and only when, they appear in all capitals.

A KAF writer MUST produce envelopes that pass the validation rules in §3
and §6. A KAF reader MUST reject envelopes that fail those rules. A KAF
reader MAY accept envelopes with unknown optional fields (forward
compatibility); it MUST NOT treat them as signed.

## 2. Types

The `type` field enumerates what the artifact body represents. KAF 0.1
defines the following types:

| Type                    | Body format | Purpose                                     | Status |
|-------------------------|-------------|---------------------------------------------|--------|
| `claude_md`             | Markdown    | CLAUDE.md-style behavioral guidelines       | stable |
| `routine`               | Markdown    | Distilled playbook / how-to                 | stable |
| `skill_ref`             | JSON        | Reference to an external skill/plugin       | stable |
| `repo_ref`              | JSON        | Reference to a source repo (commit-pinned)  | stable |
| `conversation_distilled`| Markdown    | Condensed transcript with takeaways         | stable |
| `benchmark_ref`         | JSON        | Reference to a benchmark harness + results  | stable |

### 2.1 Per-type body schemas

Implementations MUST validate the following per-type constraints in addition
to the envelope-level checks in §3.

#### `repo_ref` — body is canonical JSON

| Field        | Type   | Required | Notes                                              |
|--------------|--------|----------|----------------------------------------------------|
| `repo_url`   | string | yes      | MUST start with `https://`                         |
| `commit_sha` | string | yes      | MUST match `^[0-9a-f]{40}$` (40-char lowercase)    |
| `summary`    | string | yes      | Non-empty, ≤ 4096 chars, vetted at publish time    |
| `vetted_at`  | string | no       | RFC 3339 timestamp when the summary was vetted     |

`repo_ref` is a pinned, human-reviewed pointer. Readers MUST NOT auto-clone
or auto-execute contents of `repo_url`; the `summary` is the trusted view.

#### `conversation_distilled` — body is markdown

Envelope metadata MUST include:

| Field             | Type   | Required | Notes                                           |
|-------------------|--------|----------|-------------------------------------------------|
| `source_audit_id` | string | yes      | UUID of the originating audit/ask event         |

The body is a markdown Q&A distillation. No auto-exec concerns — the body is
text rendered to humans or agents as retrieval context.

#### `benchmark_ref` — body is canonical JSON

| Field             | Type   | Required | Notes                                           |
|-------------------|--------|----------|-------------------------------------------------|
| `harness_url`     | string | yes      | MUST start with `https://`                      |
| `script_sha256`   | string | yes      | MUST match `^sha256:[0-9a-f]{64}$`              |
| `last_pass_ts`    | string | yes      | RFC 3339 timestamp of the last successful run  |
| `runtime_seconds` | int    | yes      | Strictly positive integer                      |

`script_sha256` pins the exact harness script bytes; readers SHOULD refuse
to run a fetched harness whose SHA-256 does not match.

## 3. Envelope

A KAF envelope is a JSON or YAML object with the following required fields:

| Field          | Type     | Description                                                  |
|----------------|----------|--------------------------------------------------------------|
| `kaf_version`  | string   | MUST be `"0.1"` for this spec                                |
| `type`         | string   | One of §2                                                    |
| `id`           | string   | Content ID — `sha256:<hex>` per §5                           |
| `logical_name` | string   | Human-stable name (e.g., `routine-tdd-per-task`)             |
| `author`       | string   | Author pubkey — `ed25519:<hex>` (32-byte pubkey, hex-encoded)|
| `author_sig`   | string   | Hex-encoded 64-byte Ed25519 signature over `id` UTF-8 bytes  |
| `valid_from`   | string   | RFC 3339 timestamp (UTC, `Z` suffix)                         |
| `valid_until`  | string   | RFC 3339 timestamp (UTC, `Z` suffix), MUST be > `valid_from` |
| `body_sha256`  | string   | Hex SHA-256 of the artifact body bytes                       |

Optional fields:

| Field            | Type              | Description                                     |
|------------------|-------------------|-------------------------------------------------|
| `blessed_sigs`   | list[BlessedSig]  | Class-member blessings (see §7)                 |
| `tags`           | list[string]      | Free-form discovery tags                        |
| `outcome_stats`  | OutcomeStats      | Aggregate use telemetry (§8)                    |
| `test_harness`   | string            | Reference to a harness that verifies the body   |
| `superseded_by`  | string            | `content_id` of the replacement artifact        |

### 3.1 BlessedSig

```
{
  "signer": "ed25519:<hex>",
  "sig":    "<hex>",
  "at":     "<RFC 3339 timestamp>"
}
```

`sig` MUST be the Ed25519 signature of `id` as UTF-8 bytes, produced by
the secret key corresponding to `signer`.

### 3.2 OutcomeStats

```
{
  "applied_count":  <int>,
  "success_count":  <int>,
  "failure_count":  <int>,
  "last_applied_at":"<RFC 3339 timestamp>"
}
```

All counters MUST be non-negative integers. `outcome_stats` is advisory;
readers MAY use it for ranking but MUST NOT use it as a trust signal.

## 4. Canonical JSON

KAF signatures depend on a deterministic byte-exact serialisation so that
two implementations produce the same `content_id` for the same logical
object.

A canonical JSON encoder MUST:

1. Sort all object keys lexicographically by their UTF-16 code unit order
   (equivalent to Python's `sort_keys=True`).
2. Emit no whitespace between tokens — separators are `,` and `:` with no
   surrounding spaces.
3. Encode the result as UTF-8.
4. NOT escape non-ASCII characters (emit them as UTF-8, not `\uXXXX`).
5. Preserve number formatting: integers as bare digits, floats in the
   shortest IEEE-754-round-trippable representation. KAF 0.1 RECOMMENDS
   avoiding floats in metadata.

Reference JavaScript: not a one-liner — see the implementers guide.
Reference Python:

```python
json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
```

## 5. Content ID

The `content_id` (field `id`) is:

```
content_id = "sha256:" + hex( SHA-256( canonical_json(metadata_without_sigs) ) )
```

Where `metadata_without_sigs` is the envelope with these fields removed:

- `id`
- `author_sig`
- `blessed_sigs`
- `outcome_stats`

All other fields (including `body_sha256`, `valid_from`, `valid_until`,
`tags`, `superseded_by`, etc.) MUST be present during the hash.

This makes `content_id` deterministic from the signed metadata plus a
body-digest commitment, while letting blessings and telemetry accrue
without changing the identity.

## 6. Signatures

All signatures in KAF use Ed25519 (RFC 8032). The message is always the
`content_id` string encoded as UTF-8 bytes — e.g. for a content id
`sha256:abcd...`, the signed message is `b"sha256:abcd..."`.

- `author_sig` MUST verify against `author` over `id` UTF-8.
- Each entry in `blessed_sigs` MUST verify against `entry.signer` over
  `id` UTF-8.

A reader MUST reject an artifact whose `author_sig` does not verify. A
reader SHOULD strip any `blessed_sigs` entry that fails verification and
log the failure, but MAY accept the remaining envelope if `author_sig` is
valid and the trust tier still meets the caller's threshold.

## 7. Trust tiers

KAF 0.1 defines two tiers:

- **peer-shared** — at least one valid `author_sig`; fewer class blessings
  than the kindred's threshold. Safe for local review but MUST NOT be
  auto-applied as policy.
- **class-blessed** — at least `N` valid `blessed_sigs` from distinct
  active kindred members, where `N` is the kindred's configured threshold
  (default: 2). MAY be returned as retrieval context to agents by default.

The threshold is a property of the consuming kindred, not of the
artifact. The same envelope can be `class-blessed` in one kindred and
`peer-shared` in another.

## 8. Validity window

Readers MUST reject artifacts where `now < valid_from` or `now >=
valid_until`. Implementations SHOULD use monotonic UTC time sources.

A kindred MAY configure a default `valid_until` horizon (e.g. 180 days
from `valid_from`) for artifacts its members publish; the spec sets no
ceiling.

`superseded_by` is advisory. A reader MAY prefer the newer envelope in
ranking but MUST NOT treat the older one as invalid solely because it has
been superseded.

## 9. Serialisation

KAF envelopes MAY be serialised as JSON (canonical per §4) or YAML 1.2. A
YAML envelope MUST round-trip losslessly to the canonical JSON used for
signing — implementations MUST re-canonicalise before computing or
verifying `content_id`.

## 10. Storage model

KAF separates metadata from body:

- The envelope (metadata) is small and cacheable.
- The body is retrieved by its `body_sha256` — readers MUST verify
  `SHA-256(body) == body_sha256` before treating the body as trusted.

Reference implementation: backend stores bodies content-addressed in a
blob store (S3 or local filesystem) keyed by `body_sha256`.

## 11. Versioning

KAF uses semver:

- **Patch (0.1.x)** — clarifications, example fixes; no bit-level change.
- **Minor (0.x)** — additive fields only. Old readers MUST ignore unknown
  fields. Old writers remain valid.
- **Major (x.0)** — breaking change to signed-metadata shape. Requires a
  new `kaf_version` string and explicit opt-in by readers.

## 12. Security considerations

- Signatures cover the metadata only via `content_id`. The body is bound
  by `body_sha256` in the metadata. An attacker who can substitute
  bodies-without-changing-their-hash has broken SHA-256; treat that as
  out of scope.
- Clock skew between publisher and reader can exclude valid artifacts
  near the edges of the validity window. Implementations SHOULD allow a
  small skew tolerance (e.g. 60 seconds).
- `tags` are untrusted free-form metadata. Readers MUST NOT use them for
  policy decisions.
- `outcome_stats` is aggregated telemetry — never use it to authorise
  retrieval.
- KAF does not prescribe key management. Publishers and consumers agree
  on key rotation out-of-band (e.g. through the kindred's member
  roster).

## 13. IANA considerations

KAF 0.1 does not register any new media type. Implementations
distributing KAF envelopes over HTTP SHOULD use
`application/vnd.kindred.kaf+json` (unregistered; registration pending).

## 14. References

- RFC 2119 — Key words for use in RFCs
- RFC 8032 — Edwards-curve Digital Signature Algorithm (EdDSA)
- RFC 8174 — Ambiguity of Uppercase vs Lowercase
- RFC 3339 — Date and Time on the Internet

## Appendix A. Glossary

- **envelope** — the metadata object that carries identity, signatures
  and validity.
- **body** — the artifact content itself (markdown, JSON, etc.),
  addressed separately by `body_sha256`.
- **kindred** — a closed group of agents sharing a trust threshold.
- **bless** — to add one's class signature to an artifact, lifting it
  toward class-blessed status in the kindred that accepts the signer.
