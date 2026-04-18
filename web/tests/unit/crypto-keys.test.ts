/**
 * Parity tests vs. backend's canonical_json + content_id + Ed25519.
 *
 * Vectors sourced from backend/tests/kaf/vectors.json. Any drift here means
 * the web-side signing won't round-trip through the backend, so this is a
 * hard correctness gate, not a nice-to-have.
 */
import { describe, it, expect } from "vitest";
import {
  canonicalJson,
  contentId,
  contentIdBytes,
  generateKeypair,
  hex,
  hexToBytes,
  pubkeyFromStr,
  pubkeyToStr,
  sign,
  verify,
} from "@/lib/crypto/keys";
import * as ed from "@noble/ed25519";

describe("canonicalJson", () => {
  it("v1: empty dict -> {}", () => {
    expect(hex(canonicalJson({}))).toBe("7b7d");
    expect(new TextDecoder().decode(canonicalJson({}))).toBe("{}");
  });

  it("v2: sorted keys", () => {
    const bytes = canonicalJson({ a: 1, b: 2 });
    expect(hex(bytes)).toBe("7b2261223a312c2262223a327d");
    expect(new TextDecoder().decode(bytes)).toBe('{"a":1,"b":2}');
  });

  it("v3: unsorted input produces identical canonical output", () => {
    const unsorted = canonicalJson({ b: 2, a: 1 });
    const sorted = canonicalJson({ a: 1, b: 2 });
    expect(hex(unsorted)).toBe(hex(sorted));
    expect(hex(unsorted)).toBe("7b2261223a312c2262223a327d");
  });

  it("v4: nested dict + array", () => {
    const bytes = canonicalJson({ x: [3, 1, 2], y: { b: 1, a: 2 } });
    expect(hex(bytes)).toBe(
      "7b2278223a5b332c312c325d2c2279223a7b2261223a322c2262223a317d7d"
    );
    expect(new TextDecoder().decode(bytes)).toBe(
      '{"x":[3,1,2],"y":{"a":2,"b":1}}'
    );
  });
});

describe("contentId", () => {
  it("v1: sha256 over canonical {} ", () => {
    expect(contentId({})).toBe(
      "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
    );
  });

  it("v2: sha256 over canonical {a:1,b:2}", () => {
    expect(contentId({ a: 1, b: 2 })).toBe(
      "sha256:43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    );
  });

  it("v4: nested", () => {
    expect(contentId({ x: [3, 1, 2], y: { b: 1, a: 2 } })).toBe(
      "sha256:45ac223e0380e306b0cdda0fe1ddb6770ce35be66fd793f11fecc66a5b26f23e"
    );
  });

  it("v5: sha256 over raw bytes 'hello world'", () => {
    const bytes = new TextEncoder().encode("hello world");
    expect(contentIdBytes(bytes)).toBe(
      "sha256:b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    );
  });
});

describe("ed25519 signing", () => {
  it("sig_v1: deterministic signature with sk=00*32 matches backend", async () => {
    const sk = hexToBytes(
      "0000000000000000000000000000000000000000000000000000000000000000"
    );
    const pk = await ed.getPublicKeyAsync(sk);
    expect(hex(pk)).toBe(
      "3b6a27bcceb6a42d62a3a8d02a6f0d73653215771de243a63ac048a18b59da29"
    );
    const message = new TextEncoder().encode(
      "sha256:b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    );
    const sig = await sign(sk, message);
    expect(hex(sig)).toBe(
      "5d430c81d084a05f510a25a203fa645257c1b29070a05dc348e0298e0f8eac3260050907fb30a9f505dd3afe0b6237601bde9d020c06320ede3c1fcb6bddc902"
    );
  });

  it("round-trips a fresh keypair", async () => {
    const { sk, pk } = await generateKeypair();
    const msg = new TextEncoder().encode("some canonical bytes");
    const sig = await sign(sk, msg);
    expect(await verify(pk, msg, sig)).toBe(true);
    // Mutated message fails verification.
    const bad = new TextEncoder().encode("some canonical byte*");
    expect(await verify(pk, bad, sig)).toBe(false);
  });
});

describe("pubkey encoding", () => {
  it("round-trips pubkeyToStr / pubkeyFromStr", () => {
    const bytes = new Uint8Array(32).fill(7);
    const s = pubkeyToStr(bytes);
    expect(s).toBe("ed25519:" + "07".repeat(32));
    expect(hex(pubkeyFromStr(s))).toBe("07".repeat(32));
  });

  it("rejects unknown prefix", () => {
    expect(() => pubkeyFromStr("x25519:aa")).toThrow();
  });
});
