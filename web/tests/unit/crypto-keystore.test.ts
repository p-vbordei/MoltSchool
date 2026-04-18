import { describe, it, expect, beforeEach } from "vitest";
import "fake-indexeddb/auto";
import {
  deleteKeypair,
  listKeypairs,
  loadKeypair,
  saveKeypair,
} from "@/lib/crypto/keystore";

describe("keystore", () => {
  beforeEach(async () => {
    const req = indexedDB.deleteDatabase("kindred-keystore");
    await new Promise((r) => {
      req.onsuccess = () => r(null);
      req.onerror = () => r(null);
      req.onblocked = () => r(null);
    });
  });

  it("saves and loads a keypair", async () => {
    const sk = new Uint8Array(32).fill(1);
    const pk = new Uint8Array(32).fill(2);
    await saveKeypair("owner-u1", sk, pk);
    const loaded = await loadKeypair("owner-u1");
    expect(loaded).not.toBeNull();
    expect(Array.from(loaded!.sk)).toEqual(Array.from(sk));
    expect(Array.from(loaded!.pk)).toEqual(Array.from(pk));
  });

  it("returns null for missing id", async () => {
    expect(await loadKeypair("nope")).toBeNull();
  });

  it("lists stored ids", async () => {
    await saveKeypair("a", new Uint8Array(32), new Uint8Array(32));
    await saveKeypair("b", new Uint8Array(32), new Uint8Array(32));
    const ids = await listKeypairs();
    expect(ids.sort()).toEqual(["a", "b"]);
  });

  it("deletes a keypair", async () => {
    await saveKeypair("tmp", new Uint8Array(32), new Uint8Array(32));
    await deleteKeypair("tmp");
    expect(await loadKeypair("tmp")).toBeNull();
  });
});
