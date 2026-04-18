from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from kindred.api.middleware import install_middleware
from kindred.api.routers import agents, artifacts, health, kindreds, users
from kindred.errors import (
    ConflictError,
    KindredError,
    NotFoundError,
    SignatureError,
    UnauthorizedError,
    ValidationError,
)

app = FastAPI(title="Kindred Backend", version="0.1.0")
install_middleware(app)
app.include_router(health.router)
app.include_router(users.router, prefix="/v1/users", tags=["users"])
app.include_router(agents.router, prefix="/v1/users", tags=["agents"])
app.include_router(kindreds.router, prefix="/v1/kindreds", tags=["kindreds"])
app.include_router(artifacts.router, prefix="/v1/kindreds", tags=["artifacts"])


@app.exception_handler(KindredError)
async def kindred_error_handler(request: Request, exc: KindredError):
    status = {
        NotFoundError: 404,
        ConflictError: 409,
        ValidationError: 400,
        SignatureError: 401,
        UnauthorizedError: 403,
    }.get(type(exc), 500)
    return JSONResponse(
        status_code=status,
        content={"error": type(exc).__name__, "message": str(exc)},
    )
