import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        resp = await call_next(request)
        resp.headers["x-request-id"] = rid
        return resp


def install_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestIdMiddleware)
