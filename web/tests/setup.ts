import "@testing-library/jest-dom/vitest";
import { webcrypto } from "node:crypto";

// jsdom ships a strict SubtleCrypto polyfill that rejects Uint8Array.buffer in
// some paths (observed from @noble/ed25519's sha512Async on Node 20 in CI).
// Delegate to Node's native webcrypto, which accepts the same inputs that
// browsers do — keeping behaviour between test and production aligned.
Object.defineProperty(globalThis, "crypto", {
  value: webcrypto,
  configurable: true,
  writable: true,
});
