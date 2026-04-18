/**
 * Client-side crypto primitives.
 *
 * Ed25519 signing + canonical JSON content hashing. Runs in the browser via
 * @noble/ed25519 (audited, zero-dep). We prefer this over raw WebCrypto
 * SubtleCrypto for Ed25519 because SubtleCrypto's Ed25519 support is uneven
 * across browsers (Safari wobbly pre-2024). SHA-256 comes from @noble/hashes.
 *
 * Canonical JSON mirrors the backend's `kindred.crypto.canonical.canonical_json`:
 * sorted keys, no whitespace, UTF-8, no ASCII escape. The KAF parity test
 * (tests/unit/crypto-keys.test.ts) verifies byte-for-byte agreement on known
 * vectors from the Python side.
 */
import * as ed from "@noble/ed25519";
import { sha256 } from "@noble/hashes/sha2.js";

/**
 * Canonical JSON matching Python's
 * `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
 *
 * JS's `JSON.stringify` already matches Python's `ensure_ascii=False` default
 * for non-ASCII string bytes (no \uXXXX escapes), and emits no whitespace when
 * called without the space arg. We only need to sort keys manually.
 */
export function canonicalJson(obj: unknown): Uint8Array {
  function sortedStringify(v: unknown): string {
    if (v === null || typeof v !== "object") return JSON.stringify(v);
    if (Array.isArray(v)) return "[" + v.map(sortedStringify).join(",") + "]";
    const keys = Object.keys(v as Record<string, unknown>).sort();
    return (
      "{" +
      keys
        .map(
          (k) =>
            JSON.stringify(k) +
            ":" +
            sortedStringify((v as Record<string, unknown>)[k])
        )
        .join(",") +
      "}"
    );
  }
  return new TextEncoder().encode(sortedStringify(obj));
}

/** SHA-256 content_id over a canonical-JSON'd object. */
export function contentId(obj: unknown): string {
  const bytes = canonicalJson(obj);
  const hash = sha256(bytes);
  return "sha256:" + hex(hash);
}

/** SHA-256 content_id over raw bytes. */
export function contentIdBytes(data: Uint8Array): string {
  const hash = sha256(data);
  return "sha256:" + hex(hash);
}

/** Generate an Ed25519 keypair. sk is the 32-byte RFC 8032 seed. */
export async function generateKeypair(): Promise<{
  sk: Uint8Array;
  pk: Uint8Array;
}> {
  const sk = ed.utils.randomSecretKey();
  const pk = await ed.getPublicKeyAsync(sk);
  return { sk, pk };
}

/** Sign `message` bytes with sk. Returns a 64-byte Ed25519 signature. */
export async function sign(
  sk: Uint8Array,
  message: Uint8Array
): Promise<Uint8Array> {
  return ed.signAsync(message, sk);
}

/** Verify a signature. */
export async function verify(
  pk: Uint8Array,
  message: Uint8Array,
  sig: Uint8Array
): Promise<boolean> {
  return ed.verifyAsync(sig, message, pk);
}

/** Serialize a pubkey as the backend's `ed25519:<hex>` string. */
export function pubkeyToStr(pk: Uint8Array): string {
  return "ed25519:" + hex(pk);
}

/** Parse an `ed25519:<hex>` string back to raw bytes. */
export function pubkeyFromStr(s: string): Uint8Array {
  const prefix = "ed25519:";
  if (!s.startsWith(prefix)) throw new Error("invalid pubkey prefix");
  return hexToBytes(s.slice(prefix.length));
}

export function hex(bytes: Uint8Array): string {
  let out = "";
  for (let i = 0; i < bytes.length; i++) {
    out += bytes[i].toString(16).padStart(2, "0");
  }
  return out;
}

export function hexToBytes(h: string): Uint8Array {
  if (h.length % 2 !== 0) throw new Error("hex string must be even length");
  const out = new Uint8Array(h.length / 2);
  for (let i = 0; i < h.length; i += 2) {
    out[i / 2] = parseInt(h.slice(i, i + 2), 16);
  }
  return out;
}
