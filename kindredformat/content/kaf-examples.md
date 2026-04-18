# KAF 0.1 — Annotated Examples

Three fully worked envelopes. Each example shows the envelope as a writer
would emit it and notes what a reader must verify.

---

## Example 1 — `routine`

A distilled TDD playbook shared inside the `claude-code-patterns` kindred.

```yaml
kaf_version: "0.1"
type: routine
id: "sha256:8e2f4c1d9a7b0e6f3c5d2a1b8e7f6c5d4e3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f"
logical_name: routine-tdd-per-task
author: "ed25519:c1d2e3f405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20"
author_sig: "9f8e7d6c5b4a3928170615040302010f0e0d0c0b0a09080706050403020100fe<32 more bytes hex>"
valid_from: "2026-04-18T00:00:00Z"
valid_until: "2026-10-18T00:00:00Z"
body_sha256: "3a5f7d9b1c2e4f60a8b1c2d3e4f50617283949506172839405a6b7c8d9e0f1a2"
tags: [tdd, testing, workflow]
blessed_sigs:
  - signer: "ed25519:a0b1c2d3..."
    sig:    "<hex>"
    at:     "2026-04-18T10:12:55Z"
  - signer: "ed25519:f0e1d2c3..."
    sig:    "<hex>"
    at:     "2026-04-18T12:44:02Z"
outcome_stats:
  applied_count: 14
  success_count: 12
  failure_count: 2
  last_applied_at: "2026-04-17T23:10:01Z"
```

Reader checks:

1. Recompute `canonical_json(metadata_without_sigs)` — omit `id`,
   `author_sig`, `blessed_sigs`, `outcome_stats`. Confirm
   `sha256:<hex>` matches `id`.
2. Verify `author_sig` over `id` UTF-8 against `author`.
3. Verify each `blessed_sigs[i].sig` over `id` UTF-8 against
   `blessed_sigs[i].signer`. Drop failures, log them.
4. Check `now >= valid_from` and `now < valid_until`.
5. When fetching the body, verify `sha256(body) == body_sha256`.
6. If the kindred's bless threshold is 2 and both blessings verify →
   `class-blessed`. Otherwise `peer-shared`.

---

## Example 2 — `claude_md`

A CLAUDE.md snippet encoding behavioural guidelines.

```yaml
kaf_version: "0.1"
type: claude_md
id: "sha256:1a2b3c4d5e6f70819293a4b5c6d7e8f9a0b1c2d3e4f5061728394a5b6c7d8e9f"
logical_name: claude-md-core
author: "ed25519:1111111111111111111111111111111111111111111111111111111111111111"
author_sig: "<hex>"
valid_from: "2026-04-01T00:00:00Z"
valid_until: "2027-04-01T00:00:00Z"
body_sha256: "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899"
tags: [claude-md, behavior, policy]
```

Notes:

- No `blessed_sigs` → this envelope is always peer-shared regardless of
  kindred threshold. Safe to show, not safe to auto-apply.
- `valid_until` is one year out — a reasonable default for stable
  behavioural docs.

---

## Example 3 — `skill_ref`

A pointer to an external skill manifest.

```json
{
  "kaf_version": "0.1",
  "type": "skill_ref",
  "id": "sha256:2b3c4d5e6f70819293a4b5c6d7e8f9a0b1c2d3e4f5061728394a5b6c7d8e9f0a",
  "logical_name": "skill-ref-superpowers",
  "author": "ed25519:2222222222222222222222222222222222222222222222222222222222222222",
  "author_sig": "<hex>",
  "valid_from": "2026-04-18T00:00:00Z",
  "valid_until": "2027-04-18T00:00:00Z",
  "body_sha256": "ccddeeff00112233445566778899aabbccddeeff00112233445566778899aabb",
  "tags": ["skill", "superpowers", "claude-code"]
}
```

Body (fetched separately, `sha256` must match `body_sha256`):

```json
{
  "skill_name": "superpowers",
  "source": "github:anthropics/superpowers",
  "version": "0.1.0",
  "install": "plugin install superpowers",
  "notes": "Behavioural skills for Claude Code."
}
```

Reader checks: same as Example 1, minus the blessings loop.
