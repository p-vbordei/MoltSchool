import time
import uuid
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from kindred.config import Settings


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        resp = await call_next(request)
        resp.headers["x-request-id"] = rid
        return resp


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings | None = None):
        super().__init__(app)
        self._settings = settings
        self._buckets: dict[tuple[str, str], list[float]] = defaultdict(list)

    def _get_settings(self) -> Settings:
        if self._settings is None:
            from kindred.api.deps import get_settings
            self._settings = get_settings()
        return self._settings

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # Public /install endpoint: rate-limit by client IP (no pubkey required).
        if method == "POST" and path.endswith("/install"):
            ip = self._client_ip(request)
            s = self._get_settings()
            limit = s.rate_limit_install_per_hour
            window = 3600
            bucket_key = (ip, "install")
            now = time.monotonic()
            bucket = self._buckets[bucket_key]
            bucket[:] = [t for t in bucket if now - t < window]
            if len(bucket) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"error": "RateLimit", "message": f"exceeded {limit}/{window}s"},
                )
            bucket.append(now)
            return await call_next(request)

        pubkey = request.headers.get("x-agent-pubkey") or request.headers.get("x-owner-pubkey")
        if not pubkey:
            return await call_next(request)
        bucket_key, limit, window = self._classify(path, method, pubkey)
        if bucket_key is None:
            return await call_next(request)
        now = time.monotonic()
        bucket = self._buckets[bucket_key]
        bucket[:] = [t for t in bucket if now - t < window]
        if len(bucket) >= limit:
            return JSONResponse(
                status_code=429,
                content={"error": "RateLimit", "message": f"exceeded {limit}/{window}s"},
            )
        bucket.append(now)
        return await call_next(request)

    @staticmethod
    def _client_ip(request: Request) -> str:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _classify(self, path: str, method: str, pubkey: str):
        s = self._get_settings()
        if path.endswith("/ask"):
            return (pubkey, "ask"), s.rate_limit_ask_per_min, 60
        # POST /v1/kindreds/{slug}/artifacts (contribute) — 4 slashes, not /bless
        if (
            method == "POST"
            and "/artifacts" in path
            and not path.endswith("/bless")
            and path.count("/") == 4
        ):
            return (pubkey, "contribute"), s.rate_limit_contribute_per_hour, 3600
        return None, 0, 0


def install_middleware(app: FastAPI, settings: Settings | None = None) -> None:
    app.add_middleware(RequestIdMiddleware)
    # Settings is resolved lazily on first request to avoid requiring env at import time.
    app.add_middleware(RateLimitMiddleware, settings=settings)
