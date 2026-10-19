from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.assessment.api import router as assessment_router
from app.config import settings
from app.db import database_is_reachable
from app.inventory.api import router as inventory_router
from app.questionnaire.api import assessments_router, questionnaire_router

app = FastAPI(title="Sovereignty Assessment Copilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)
app.include_router(inventory_router)
app.include_router(assessment_router)
app.include_router(questionnaire_router)
app.include_router(assessments_router)


@app.exception_handler(HTTPException)
async def error_format(request: Request, exc: HTTPException) -> JSONResponse:
    """Alle Fehler im selben Format: {"error": {"code": ..., "message": ...}}."""
    detail = (
        exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": exc.detail}
    )
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_error_format(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Auch eine ungültige Anfrage kommt im einheitlichen Format, mit Ort und Grund je Fehler."""
    details = [
        {"location": ".".join(str(part) for part in problem["loc"]), "message": problem["msg"]}
        for problem in exc.errors()
    ]
    body = {"code": "INVALID_REQUEST", "message": "Die Anfrage ist ungültig.", "details": details}
    return JSONResponse(status_code=422, content={"error": body})


@app.get("/health")
def health(
    response: Response,
    database_ok: Annotated[bool, Depends(database_is_reachable)],
) -> dict[str, str]:
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
