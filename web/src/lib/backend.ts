/**
 * Typed fetch wrapper around /api/backend/* proxy.
 *
 * Works on both server (direct fetch to backend) and client (through the
 * proxy). When used on the server we still hit /api/backend to keep one
 * code path — in RSC, Next's internal fetch dedupes these automatically.
 */

export type Kindred = {
  slug: string;
  display_name: string;
  description?: string;
  member_count?: number;
  artifact_count?: number;
};

export type Artifact = {
  content_id: string;
  logical_name: string;
  type: string;
  valid_until?: string;
  content?: string;
  author_pubkey?: string;
  tier?: "observed" | "peer" | "blessed";
  tags?: string[];
  blessings?: Array<{ signer: string; sig: string }>;
  outcomes?: { positive: number; negative: number };
};

export type AuditEvent = {
  seq: number;
  ts: string;
  action: string;
  agent?: string;
  payload?: Record<string, unknown>;
};

export class BackendError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message);
  }
}

function resolveBase(): string {
  // On the server, the proxy route needs an absolute URL. On the client
  // relative paths resolve against window.location.
  if (typeof window === "undefined") {
    const host = process.env.NEXTAUTH_URL ?? "http://localhost:3000";
    return `${host}/api/backend`;
  }
  return "/api/backend";
}

async function request<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const url = `${resolveBase()}${path}`;
  const headers = new Headers(init?.headers);
  if (init?.json !== undefined) {
    headers.set("content-type", "application/json");
  }
  const resp = await fetch(url, {
    ...init,
    headers,
    body: init?.json !== undefined ? JSON.stringify(init.json) : init?.body,
    cache: "no-store",
  });
  if (!resp.ok) {
    let body: { error?: string; message?: string } = {};
    try {
      body = (await resp.json()) as typeof body;
    } catch {
      // swallow — fall back to status text
    }
    throw new BackendError(
      resp.status,
      body.error ?? "http_error",
      body.message ?? resp.statusText
    );
  }
  // Some endpoints return empty bodies.
  const text = await resp.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export const backend = {
  kindreds: {
    get: (slug: string) => request<Kindred>(`/kindreds/${slug}`),
    list: () => request<{ kindreds: Kindred[] }>(`/kindreds`),
    create: (body: { slug: string; display_name: string; description?: string }) =>
      request<Kindred>(`/kindreds`, { method: "POST", json: body }),
  },
  artifacts: {
    list: (slug: string) =>
      request<{ artifacts: Artifact[] }>(`/kindreds/${slug}/artifacts`),
    bless: (slug: string, cid: string, sig: string) =>
      request<{ ok: boolean }>(
        `/kindreds/${slug}/artifacts/${cid}/bless`,
        { method: "POST", json: { sig } }
      ),
  },
  audit: {
    list: (slug: string) =>
      request<{ events: AuditEvent[] }>(`/kindreds/${slug}/audit`),
  },
  invites: {
    accept: (token: string) =>
      request<{ kindred: Kindred }>(`/invites/${token}/accept`, {
        method: "POST",
      }),
  },
};
