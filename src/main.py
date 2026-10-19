import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.agent_customer import router as agent_customer_router
from src.api.auth import router as auth_router
from src.api.cases import router as cases_router
from src.api.customer import router as customer_router
from src.api.customer_memory import router as customer_memory_router
from src.api.public import router as public_router
from src.api.routes import router
from src.api.staff import router as staff_router
from src.config import get_settings
from src.db import ensure_schema
from src.models import db_models  # noqa: F401 - Đảm bảo tất cả models được nạp vào metadata
from src.services.case_lifecycle import auto_close_background_loop
from src.services.observability import flush_observability, initialize_observability
from src.services.location_privacy import LocationQueryPrivacyMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Tự động đảm bảo các bảng trong SQLite DB và thư mục lưu trữ đã được tạo
    os.makedirs("data/attachments", exist_ok=True)
    ensure_schema()
    import logging
    from sqlalchemy import func, select
    from src.db import SessionLocal
    from src.models.db_models import ServicePoint
    logger = logging.getLogger(__name__)

    catalog_mode = os.environ.get("GPS_CATALOG_MODE", "auto").strip().lower()
    with SessionLocal() as db_session:
        try:
            sp_count = db_session.scalar(select(func.count()).select_from(ServicePoint)) or 0
        except Exception:
            sp_count = 0

    logger.info("Service points count: %d, GPS_CATALOG_MODE: %s", sp_count, catalog_mode)
    if sp_count == 0:
        logger.warning("service_points trống, đang dùng snapshot — chạy import_service_points")

    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    initialize_observability()
    auto_close_task = asyncio.create_task(auto_close_background_loop(interval_seconds=600))
    try:
        yield
    finally:
        auto_close_task.cancel()
        try:
            await auto_close_task
        except asyncio.CancelledError:
            pass
        finally:
            await flush_observability(shutdown=True)
            print("Shutting down...")


app = FastAPI(
    title="VinFast ServiceFlow AI",
    description="VinFast Customer Service & Incident Triage AI Agent built with LangGraph",
    version="1.1.0",
    lifespan=lifespan,
)

settings = get_settings()
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if "*" not in origins and "http://localhost:3000" not in origins:
    origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LocationQueryPrivacyMiddleware)

# Đăng ký các Router API
app.include_router(agent_customer_router, prefix="/api/v1/agent")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(customer_router, prefix="/api/v1")
app.include_router(customer_memory_router, prefix="/api/v1")
app.include_router(staff_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env, "service": "VFServ"}
