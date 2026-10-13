from typing import Annotated

from fastapi import Depends, FastAPI, Response, status

from app.db import database_is_reachable

app = FastAPI(title="Sovereignty Assessment Copilot")


@app.get("/health")
def health(
    response: Response,
    database_ok: Annotated[bool, Depends(database_is_reachable)],
) -> dict[str, str]:
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
