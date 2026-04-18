import { NextRequest, NextResponse } from "next/server";
import { env } from "@/lib/env";
import { getSessionKeys } from "@/lib/session";

export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ path: string[] }> };

async function proxy(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  const segments = path?.join("/") ?? "";
  const qs = req.nextUrl.search;
  const url = `${env.backendUrl}/v1/${segments}${qs}`;

  const keys = await getSessionKeys();

  const headers = new Headers();
  headers.set("content-type", "application/json");
  if (keys?.ownerPubkey) headers.set("x-owner-pubkey", keys.ownerPubkey);
  if (keys?.agentPubkey) headers.set("x-agent-pubkey", keys.agentPubkey);

  const init: RequestInit = {
    method: req.method,
    headers,
    cache: "no-store",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    const text = await req.text();
    if (text) init.body = text;
  }

  let resp: Response;
  try {
    resp = await fetch(url, init);
  } catch (err) {
    const message = err instanceof Error ? err.message : "backend unreachable";
    return NextResponse.json(
      { error: "backend_unreachable", message },
      { status: 502 }
    );
  }

  // Strip server internals from error responses to avoid leaking stack traces.
  if (!resp.ok) {
    let body: unknown;
    try {
      body = await resp.json();
    } catch {
      body = { error: "upstream_error", message: `status ${resp.status}` };
    }
    const safe =
      typeof body === "object" && body !== null
        ? {
            error: (body as { error?: string }).error ?? "upstream_error",
            message: (body as { message?: string; detail?: string }).message ??
              (body as { message?: string; detail?: string }).detail ??
              `status ${resp.status}`,
          }
        : { error: "upstream_error", message: `status ${resp.status}` };
    return NextResponse.json(safe, { status: resp.status });
  }

  const ct = resp.headers.get("content-type") ?? "application/json";
  const buf = await resp.arrayBuffer();
  return new NextResponse(buf, {
    status: resp.status,
    headers: { "content-type": ct },
  });
}

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}
export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}
export async function DELETE(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}
export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}
