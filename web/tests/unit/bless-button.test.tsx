import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BlessButton } from "@/components/bless-button";

// next/navigation is not shipped to jsdom — provide a stub.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

describe("BlessButton", () => {
  const origFetch = globalThis.fetch;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as unknown as typeof fetch;
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
    render(<BlessButton kindredSlug="coven" contentId="abc" />);
    fireEvent.click(screen.getByRole("button", { name: "Bless" }));
    expect(
      screen.getByRole("heading", { name: /Bless this artifact/i })
    ).toBeInTheDocument();
  });

  it("POSTs to the bless endpoint on confirm", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );
    render(<BlessButton kindredSlug="coven" contentId="bafybeiabc" />);
    fireEvent.click(screen.getByRole("button", { name: "Bless" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Bless" })[1]);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe(
      "/api/backend/kindreds/coven/artifacts/bafybeiabc/bless"
    );
    expect(init.method).toBe("POST");
  });
});
