# KAF 0.1 Implementers Guide

A short, bit-level guide for someone writing a KAF 0.1 reader or writer
in any language. All algorithms are specified against their observable
byte output so cross-language implementations can verify byte-for-byte
equivalence.

---

## 1. Canonical JSON

Required behaviour:

1. Sort object keys lexicographically by UTF-16 code unit order.
2. Separators are exactly `,` and `:` — no spaces.
3. Do NOT escape non-ASCII characters. Emit them as raw UTF-8 bytes.
4. Integers emit as bare digits. Avoid floats in KAF metadata.
5. Emit `true`, `false`, `null` lowercase.
6. The output byte stream is UTF-8.

### Python

```python
import json

def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
```

### TypeScript / Node

`JSON.stringify` does NOT sort keys and DOES escape non-ASCII. Implement
manually:

```ts
export function canonicalJson(value: unknown): Uint8Array {
  const s = stringify(value);
  return new TextEncoder().encode(s);
}

function stringify(v: unknown): string {
  if (v === null) return "null";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) throw new Error("non-finite");
    return Number.isInteger(v) ? v.toString() : v.toString();
  }
  if (typeof v === "string") return JSON.stringify(v); // native handles escapes for control chars
  if (Array.isArray(v)) return "[" + v.map(stringify).join(",") + "]";
  if (typeof v === "object") {
    const keys = Object.keys(v as object).sort();
    return "{" + keys.map(k => JSON.stringify(k) + ":" + stringify((v as any)[k])).join(",") + "}";
  }
  throw new Error("unsupported type");
}
```

Note: `JSON.stringify` for strings happens to produce the same escape
set KAF expects for control chars and quotes, while leaving non-ASCII
untouched — that matches §4.4.

### Go

```go
import "encoding/json"

func CanonicalJSON(v any) ([]byte, error) {
    // Marshal, then re-marshal through a map walk to guarantee key sort.
    b, err := json.Marshal(v)
    if err != nil { return nil, err }
    var any0 any
    if err := json.Unmarshal(b, &any0); err != nil { return nil, err }
    return sortMarshal(any0)
}
// sortMarshal: recurse, sort map keys, emit without extra whitespace.
```

Go's `encoding/json` sorts map keys by default and emits compact output;
the only gotcha is non-ASCII which it escapes. Set `SetEscapeHTML(false)`
on an `Encoder` and you're close — you still need a custom encoder to
disable `\uXXXX` for non-ASCII. Most Go impls of canonical JSON for
cryptographic hashing use the `gibson042/canonicaljson-go` package or a
re-implementation.

### Rust

Use `serde_json` with a custom value walker; key sort is not the default
for `Map` unless you enable `preserve_order = false` and explicitly sort
the keys before serialising.

---

## 2. SHA-256 of canonical bytes

After producing canonical bytes `C`:

```
content_id = "sha256:" + lowercase_hex( SHA-256(C) )
```

All implementations must use the lower-case hex alphabet.

---

## 3. Ed25519 signatures

- Key format: 32-byte raw pubkey, lower-case hex, prefixed `ed25519:`.
- Signature format: 64-byte raw signature, lower-case hex (128 chars).
- Message to sign: `content_id` encoded as UTF-8 bytes.

Libraries known to be interop-tested:

| Language  | Library                         |
|-----------|---------------------------------|
| Python    | `PyNaCl` (`nacl.signing`)       |
| TypeScript| `@noble/ed25519`                |
| Go        | `crypto/ed25519` (stdlib)       |
| Rust      | `ed25519-dalek`                 |

---

## 4. Reference test vectors

Implementers MUST pass these vectors byte-for-byte.

### Vector 1 — canonical_json

Input:

```json
{"b": 2, "a": 1}
```

Output bytes (exact):

```
{"a":1,"b":2}
```

(13 bytes, UTF-8.)

### Vector 2 — canonical_json with unicode

Input:

```json
{"name": "naïve", "k": 1}
```

Output bytes:

```
{"k":1,"name":"naïve"}
```

The `ï` is emitted as the two UTF-8 bytes `0xC3 0xAF`, NOT as `\u00ef`.

### Vector 3 — content_id

Input metadata (for hashing — no `id`, no signatures, no outcome_stats):

```json
{"author":"ed25519:11","body_sha256":"00","kaf_version":"0.1","logical_name":"t","type":"routine","valid_from":"2026-04-18T00:00:00Z","valid_until":"2026-10-18T00:00:00Z"}
```

SHA-256: `be5fc6d4e88fe6d66a3c35d34c51e89b4f30cd6be7d53e60ab7c3f0c2e1c3c3a` *(illustrative)*

`content_id = "sha256:be5fc6d4e88fe6d66a3c35d34c51e89b4f30cd6be7d53e60ab7c3f0c2e1c3c3a"`

*(Note: the hex above is a stand-in; a canonical test vector is shipped
in `backend/tests/kaf/vectors.json` in the reference implementation.
Implementers should lift exact-byte vectors from that file.)*

### Vector 4 — signature verifies

Using a well-known Ed25519 seed (RFC 8032 §7.1 test case 1) — secret
key `9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60`,
pubkey `d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a`.
Sign the message `sha256:0000000000000000000000000000000000000000000000000000000000000000`
(UTF-8, 71 bytes). The resulting 64-byte signature (hex) is the expected
author_sig for that `content_id`.

### Vector 5 — blessing adds to same content_id

Given a valid envelope from Vector 3 and a second Ed25519 keypair,
producing a blessed_sigs entry MUST NOT alter `content_id`. A reader
that recomputes `content_id` before and after adding a blessing MUST
obtain the same value both times. If it does not, the implementation
is incorrectly hashing `blessed_sigs` into `content_id`.

---

## 5. Minimal reader pseudo-code

```
read(envelope_json):
    env = parse_json(envelope_json)
    assert env.kaf_version == "0.1"
    meta_for_hash = remove_keys(env, {"id","author_sig","blessed_sigs","outcome_stats"})
    computed_id = "sha256:" + sha256_hex(canonical_json(meta_for_hash))
    assert computed_id == env.id
    assert ed25519_verify(env.author, env.id.utf8(), env.author_sig)
    now = utc_now()
    assert now >= parse_rfc3339(env.valid_from)
    assert now  < parse_rfc3339(env.valid_until)
    kept = []
    for b in env.blessed_sigs or []:
        if ed25519_verify(b.signer, env.id.utf8(), b.sig):
            kept.append(b)
    return Envelope(..., blessed_sigs=kept)
```

---

## 6. Minimal writer pseudo-code

```
write(type, logical_name, author_sk, author_pk, body_bytes, validity_days, tags=[]):
    body_sha = sha256_hex(body_bytes)
    meta = {
      "kaf_version": "0.1",
      "type": type,
      "logical_name": logical_name,
      "author": "ed25519:" + hex(author_pk),
      "valid_from": now_rfc3339(),
      "valid_until": now_plus_days_rfc3339(validity_days),
      "body_sha256": body_sha,
      "tags": tags,
    }
    cid = "sha256:" + sha256_hex(canonical_json(meta))
    sig = ed25519_sign(author_sk, cid.utf8())
    meta["id"] = cid
    meta["author_sig"] = hex(sig)
    return meta, body_bytes
```

---

## 7. Conformance self-check

A KAF 0.1 implementation is conformant if:

- It produces bit-identical `content_id` values to the reference
  Python implementation for the 5 test vectors.
- Its signatures verify with the reference, and the reference's
  signatures verify with it.
- It rejects envelopes with `kaf_version != "0.1"`, invalid signatures,
  tampered `body_sha256`, or out-of-window `valid_from` / `valid_until`.

Implementers are encouraged to publish their test vector outputs under
`<project>/kaf-vectors.json` so readers from other stacks can cross-check.
