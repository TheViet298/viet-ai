import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import get_settings

# Tạo thư mục data/ nếu chưa có để SQLite tạo được file .db
os.makedirs("data", exist_ok=True)

settings = get_settings()
db_url = settings.database_url

# Tự động fallback về SQLite nếu DATABASE_URL trỏ PostgreSQL nhưng môi trường chưa cài psycopg
if db_url.startswith("postgresql"):
    try:
        import psycopg  # noqa: F401
    except ImportError:
        try:
            import psycopg2  # noqa: F401
        except ImportError:
            db_url = "sqlite:///./data/app.db"

is_sqlite = db_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
)


if is_sqlite:
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
