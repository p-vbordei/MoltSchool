from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from kindred.api.middleware import install_middleware
from kindred.api.routers import (
    agents,
    artifacts,
    blessings,
    health,
    invites,
    kindreds,
    memberships,
    users,
)
from kindred.api.routers import rollback as rb_router
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
app.include_router(invites.router, prefix="/v1/kindreds", tags=["invites"])
app.include_router(memberships.router, prefix="/v1", tags=["memberships"])
app.include_router(blessings.router, prefix="/v1/kindreds", tags=["blessings"])
app.include_router(rb_router.router, prefix="/v1/kindreds", tags=["rollback"])


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


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Maps decode/parse errors (bad hex, bad base64, bad datetime, bad pubkey format) to HTTP 400."""
    return JSONResponse(
        status_code=400,
        content={"error": "ValidationError", "message": str(exc)},
    )
