import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import get_settings

# Tạo thư mục data/ nếu chưa có để SQLite tạo được file .db
os.makedirs("data", exist_ok=True)

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # FastAPI chạy nhiều thread
)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
