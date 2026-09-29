from contextlib import asynccontextmanager

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router
from src.config import get_settings
from src.services.case_store import StoreError


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
    print("Shutting down...")


app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)


def error_response(status_code: int, code: str, message: str):
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "data": None,
                 "error": {"code": code, "message": message},
                 "meta": {"timestamp": datetime.now(timezone.utc).isoformat()}},
    )


@app.exception_handler(StoreError)
async def store_error_handler(_request: Request, error: StoreError):
    status = {"NOT_FOUND": 404, "FORBIDDEN": 403, "INVALID_TRANSITION": 409,
              "CONFLICT": 409}.get(error.code, 400)
    return error_response(status, error.code, str(error))


@app.exception_handler(HTTPException)
async def http_error_handler(_request: Request, error: HTTPException):
    detail = error.detail if isinstance(error.detail, dict) else {"code": "HTTP_ERROR", "message": str(error.detail)}
    return error_response(error.status_code, detail["code"], detail["message"])


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, _error: RequestValidationError):
    return error_response(422, "VALIDATION_ERROR", "Invalid request")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
