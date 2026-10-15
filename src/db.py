import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from src.config import get_settings

# Tạo thư mục data/ nếu chưa có để SQLite tạo được file .db
os.makedirs("data", exist_ok=True)

settings = get_settings()
db_url = settings.database_url

if db_url.startswith("postgresql"):
    try:
        import psycopg  # noqa: F401
    except ImportError:
        try:
            import psycopg2  # noqa: F401
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
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


def ensure_schema() -> None:
    """Tự động đảm bảo bảng và bổ sung cột còn thiếu cho cả SQLite và PostgreSQL khi schema cập nhật."""
    from sqlalchemy import inspect

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        insp = inspect(conn)
        tables = set(insp.get_table_names())

        # 1. users
        if "users" in tables:
            users_cols = {col["name"] for col in insp.get_columns("users")}
            if "full_name" not in users_cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN full_name VARCHAR(100)")
            if "phone" not in users_cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN phone VARCHAR(20)")
            if "vehicle_model" not in users_cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN vehicle_model VARCHAR(50)")
            if "mock_customer_id" not in users_cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN mock_customer_id VARCHAR(50)")
            if "is_demo" not in users_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE users ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT 0"
                    if is_sqlite
                    else "ALTER TABLE users ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT FALSE"
                )

        # 2. cases
        if "cases" in tables:
            cases_cols = {col["name"] for col in insp.get_columns("cases")}
            if "user_id" not in cases_cols:
                conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN user_id VARCHAR(36)")
            if "mock_customer_name" not in cases_cols:
                conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN mock_customer_name VARCHAR(100)")
            if "mock_customer_phone" not in cases_cols:
                conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN mock_customer_phone VARCHAR(20)")
            if "safety_status" not in cases_cols:
                conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN safety_status VARCHAR(30) DEFAULT 'unconfirmed'")
            if "safety_acknowledged_at" not in cases_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE cases ADD COLUMN safety_acknowledged_at DATETIME"
                    if is_sqlite
                    else "ALTER TABLE cases ADD COLUMN safety_acknowledged_at TIMESTAMP WITH TIME ZONE"
                )
            if "incident_version" not in cases_cols:
                conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN incident_version INTEGER DEFAULT 1")
            if "is_demo" not in cases_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE cases ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT 0"
                    if is_sqlite
                    else "ALTER TABLE cases ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT FALSE"
                )

        # 3. chat_sessions
        if "chat_sessions" in tables:
            chat_cols = {col["name"] for col in insp.get_columns("chat_sessions")}
            if "is_demo" not in chat_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE chat_sessions ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT 0"
                    if is_sqlite
                    else "ALTER TABLE chat_sessions ADD COLUMN is_demo BOOLEAN NOT NULL DEFAULT FALSE"
                )

        # 4. customer_feedback
        if "customer_feedback" in tables:
            fb_cols = {col["name"] for col in insp.get_columns("customer_feedback")}
            if "reason_tags" not in fb_cols:
                conn.exec_driver_sql("ALTER TABLE customer_feedback ADD COLUMN reason_tags JSON")
            if "updated_at" not in fb_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE customer_feedback ADD COLUMN updated_at DATETIME"
                    if is_sqlite
                    else "ALTER TABLE customer_feedback ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE"
                )
            try:
                conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_feedback_case_id ON customer_feedback(case_id)")
            except Exception:
                pass





def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

