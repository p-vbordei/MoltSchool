import { NextRequest, NextResponse } from "next/server";

/**
 * Strict Content-Security-Policy with per-request nonce.
 *
 * Nonce is generated for every navigation, attached to a header, and can
 * be read inside server components via `headers().get('x-nonce')` for any
 * scripts we inline. Next.js propagates the nonce to its framework scripts
 * automatically when it sees `x-nonce` on the response.
 */

function generateNonce(): string {
  const arr = new Uint8Array(16);
  crypto.getRandomValues(arr);
  let s = "";
  for (let i = 0; i < arr.length; i++) s += String.fromCharCode(arr[i]);
  // Use a URL-safe base64 encoding (atob/btoa are available in the edge runtime).
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function middleware(req: NextRequest) {
  const nonce = generateNonce();
  const backend =
    process.env.KINDRED_BACKEND_URL ?? "http://localhost:8000";

  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    `connect-src 'self' ${backend}`,
    "frame-ancestors 'none'",
    "form-action 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "upgrade-insecure-requests",
  ].join("; ");

  const requestHeaders = new Headers(req.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("content-security-policy", csp);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });

  response.headers.set("content-security-policy", csp);
  return response;
}

export const config = {
  matcher: [
    /*
     * Match everything except:
     * - static assets (_next/static, _next/image, favicon, public files)
     * - API routes (they return JSON — CSP meta doesn't apply)
     */
    {
      source: "/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)",
    },
  ],
};
