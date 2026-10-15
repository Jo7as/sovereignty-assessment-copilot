from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.db import database_is_reachable
from app.inventory.api import router as inventory_router

app = FastAPI(title="Sovereignty Assessment Copilot")
app.include_router(inventory_router)


@app.exception_handler(HTTPException)
async def error_format(request: Request, exc: HTTPException) -> JSONResponse:
    """Alle Fehler im selben Format: {"error": {"code": ..., "message": ...}}."""
    detail = (
        exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": exc.detail}
    )
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.get("/health")
def health(
    response: Response,
    database_ok: Annotated[bool, Depends(database_is_reachable)],
) -> dict[str, str]:
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
