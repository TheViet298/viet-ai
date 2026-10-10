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


def ensure_schema() -> None:
    """Tự động đảm bảo bảng và bổ sung cột còn thiếu cho SQLite khi schema cập nhật."""
    Base.metadata.create_all(bind=engine)
    if is_sqlite:
        with engine.begin() as conn:
            # Bổ sung các cột mới cho users nếu thiếu
            users_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()}
            if users_cols:
                if "full_name" not in users_cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN full_name VARCHAR(100)")
                if "phone" not in users_cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN phone VARCHAR(20)")
                if "vehicle_model" not in users_cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN vehicle_model VARCHAR(50)")
                if "mock_customer_id" not in users_cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN mock_customer_id VARCHAR(50)")

            # Bổ sung các cột mới cho cases nếu thiếu
            cases_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(cases)").fetchall()}
            if cases_cols:
                if "user_id" not in cases_cols:
                    conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN user_id VARCHAR(36)")
                if "mock_customer_name" not in cases_cols:
                    conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN mock_customer_name VARCHAR(100)")
                if "mock_customer_phone" not in cases_cols:
                    conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN mock_customer_phone VARCHAR(20)")
                if "safety_status" not in cases_cols:
                    conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN safety_status VARCHAR(30) DEFAULT 'unconfirmed'")
                if "safety_acknowledged_at" not in cases_cols:
                    conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN safety_acknowledged_at DATETIME")
                if "incident_version" not in cases_cols:
                    conn.exec_driver_sql("ALTER TABLE cases ADD COLUMN incident_version INTEGER DEFAULT 1")

            # Bổ sung các cột mới cho customer_feedback nếu thiếu
            fb_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(customer_feedback)").fetchall()}
            if fb_cols:
                if "reason_tags" not in fb_cols:
                    conn.exec_driver_sql("ALTER TABLE customer_feedback ADD COLUMN reason_tags JSON")
                if "updated_at" not in fb_cols:
                    conn.exec_driver_sql("ALTER TABLE customer_feedback ADD COLUMN updated_at DATETIME")
                try:
                    conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_feedback_case_id ON customer_feedback(case_id)")
                except Exception:
                    pass

            # Khởi tạo thông tin hồ sơ mẫu nếu đang bị NULL
            conn.exec_driver_sql(
                "UPDATE users SET full_name = 'Nguyễn Văn Tuấn', phone = '0912345678', vehicle_model = 'VF8' "
                "WHERE username = 'customer@vinfast.vn' AND (full_name IS NULL OR full_name = '')"
            )
            conn.exec_driver_sql(
                "UPDATE users SET full_name = 'Trần Thị Mai', phone = '0987654321', vehicle_model = 'VF5' "
                "WHERE username = 'customer2@vinfast.vn' AND (full_name IS NULL OR full_name = '')"
            )
            conn.exec_driver_sql(
                "UPDATE users SET full_name = 'Cố vấn Dịch vụ VinFast', phone = '1900232389' "
                "WHERE username = 'staff@vinfast.vn' AND (full_name IS NULL OR full_name = '')"
            )





def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

