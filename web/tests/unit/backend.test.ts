import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { backend, BackendError } from "@/lib/backend";

describe("backend client", () => {
  const origFetch = globalThis.fetch;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    // jsdom provides window — force server-side path to exercise absolute URL.
  });

  afterEach(() => {
    globalThis.fetch = origFetch;
    vi.restoreAllMocks();
  });

  it("calls proxy for kindred get", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ slug: "coven", display_name: "Coven" }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    const k = await backend.kindreds.get("coven");
    expect(k.slug).toBe("coven");
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/backend\/kindreds\/coven$/);
  });

  it("sends JSON body on create", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ slug: "x", display_name: "X" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      })
    );
    await backend.kindreds.create({ slug: "x", display_name: "X" });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ slug: "x", display_name: "X" }));
  });

  it("throws BackendError with sanitized shape on upstream error", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ error: "forbidden", message: "no access" }),
        { status: 403, headers: { "content-type": "application/json" } }
      )
    );
    await expect(backend.kindreds.get("secret")).rejects.toMatchObject({
      status: 403,
      code: "forbidden",
    });
    await expect(backend.kindreds.get("secret")).rejects.toBeInstanceOf(
      BackendError
    );
  });
});
