import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.cases import router as cases_router
from src.api.customer import router as customer_router
from src.api.public import router as public_router
from src.api.routes import router
from src.api.staff import router as staff_router
from src.config import get_settings
from src.db import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Tự động đảm bảo các bảng trong SQLite DB và thư mục lưu trữ đã được tạo
    os.makedirs("data/attachments", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    yield
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

# Đăng ký các Router API
app.include_router(auth_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(customer_router, prefix="/api/v1")
app.include_router(staff_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
