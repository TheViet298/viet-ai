from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import cases, health

app = FastAPI(title="VinFast ServiceFlow AI", version="0.1.0")

# Cho frontend gọi từ origin khác khi dev (siết lại origin khi deploy)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(cases.router, prefix="/api/v1")