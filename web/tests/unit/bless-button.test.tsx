import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "fake-indexeddb/auto";
import { BlessButton } from "@/components/bless-button";
import { saveKeypair } from "@/lib/crypto/keystore";
import { generateKeypair, pubkeyToStr } from "@/lib/crypto/keys";

// next/navigation is not shipped to jsdom — provide a stub.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

describe("BlessButton", () => {
  const origFetch = globalThis.fetch;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    // Reset the fake IDB between tests so one test's keys don't bleed.
    const req = indexedDB.deleteDatabase("kindred-keystore");
    await new Promise((r) => {
      req.onsuccess = () => r(null);
      req.onerror = () => r(null);
      req.onblocked = () => r(null);
    });
  });
  afterEach(() => {
    globalThis.fetch = origFetch;
    vi.restoreAllMocks();
  });

  it("shows 'you blessed this' when already blessed", () => {
    render(
      <BlessButton kindredSlug="coven" contentId="abc" alreadyBlessed />
    );
    expect(screen.getByText(/you blessed this/i)).toBeInTheDocument();
  });

  it("opens confirmation modal on click", () => {
    render(<BlessButton kindredSlug="coven" contentId="abc" userId="u1" />);
    fireEvent.click(screen.getByRole("button", { name: "Bless" }));
    expect(
      screen.getByRole("heading", { name: /Bless this artifact/i })
    ).toBeInTheDocument();
  });

  it("POSTs a real Ed25519 signature on confirm", async () => {
    // Seed the fake IDB with an agent keypair for u1.
    const { sk, pk } = await generateKeypair();
    await saveKeypair("agent-u1", sk, pk);

    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    render(
      <BlessButton
        kindredSlug="coven"
        contentId="bafybeiabc"
        userId="u1"
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Bless" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Bless" })[1]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe(
      "/api/backend/kindreds/coven/artifacts/bafybeiabc/bless"
    );
    expect(init.method).toBe("POST");

    const body = JSON.parse(init.body as string) as {
      signer_pubkey: string;
      sig: string;
    };
    expect(body.signer_pubkey).toBe(pubkeyToStr(pk));
    // 64-byte Ed25519 signature -> 128 hex chars.
    expect(body.sig).toMatch(/^[0-9a-f]{128}$/);
    // Old stub is gone.
    expect(init.body).not.toContain("server-side-v0");
  });

  it("surfaces an error when no agent keypair is present", async () => {
    render(
      <BlessButton
        kindredSlug="coven"
        contentId="bafybeiabc"
        userId="missing-user"
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Bless" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Bless" })[1]);
    await waitFor(() =>
      expect(screen.getByText(/agent key not found/i)).toBeInTheDocument()
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
