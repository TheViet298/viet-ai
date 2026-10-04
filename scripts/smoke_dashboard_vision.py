"""Live Gemini + upload/chat smoke check using the three public reference images.

Uses a temporary SQLite database and deletes downloaded reference files afterward.
Run from repository root: python -m scripts.smoke_dashboard_vision
"""

import asyncio
import json
import tempfile
from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import User
from src.services.auth import require_customer


async def main():
    catalog = json.loads(Path("dataset/img_warning_taplo/images/image_catalog.json").read_text(encoding="utf-8"))
    report = []
    expected = {
        "img_vfe34_tpms_cluster_01": ("kiểm tra lốp bên phải phía sau", "rear_right"),
        "img_vfe34_tpms_icon_low_pressure": ("tire pressure low", "rear_right"),
        "img_vfe34_tpms_icon_sensor_fault": ("tire pressure sensor fault", "front_left"),
    }
    with tempfile.TemporaryDirectory(prefix="dashboard-smoke-") as temporary:
        engine = create_engine(f"sqlite:///{Path(temporary) / 'test.db'}")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            user = User(id="vision-smoke", username="vision-smoke", password_hash="unused", role="CUSTOMER")
            db.add(user)
            db.commit()
            app.dependency_overrides[get_db] = lambda: db
            app.dependency_overrides[require_customer] = lambda: user
            try:
                async with httpx.AsyncClient(timeout=30) as remote, httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://test",
                ) as api:
                    for item in catalog:
                        source = await remote.get(item["source_url"])
                        source.raise_for_status()
                        uploaded = await api.post("/api/v1/customer/attachments", files={
                            "file": ("reference-image", source.content, source.headers.get("content-type", "image/png")),
                        })
                        uploaded.raise_for_status()
                        att = uploaded.json()["data"]
                        signals = att["detected_signals"]
                        answered = await api.post("/api/v1/customer/chat", json={
                            "session_id": item["image_id"], "message": "Ảnh táp-lô này báo gì?",
                            "attachment_ids": [att["attachment_id"]],
                            "client_context": {"vehicle_model": "VF e34"},
                        })
                        answered.raise_for_status()
                        chat = answered.json()["data"]
                        expected_text, expected_wheel = expected[item["image_id"]]
                        passed = (
                            att["analysis_status"] == "ANALYZED"
                            and sorted(signals["symptom_keys"]) == sorted(item["associated_symptom_keys"])
                            and chat["response_type"] == ("FAQ_ANSWER" if item["associated_symptom_keys"] else "CLARIFICATION")
                            and expected_text in signals.get("ocr_text", "").lower()
                            and signals.get("wheel_position") == expected_wheel
                        )
                        report.append({
                            "image_id": item["image_id"], "passed": passed,
                            "analysis_status": att["analysis_status"], "signals": signals,
                            "response_type": chat["response_type"], "reply": chat["message"],
                        })
                        # Public reference copies are only temporary test uploads.
                        Path(att["storage_key"]).unlink(missing_ok=True)
            finally:
                app.dependency_overrides.clear()
        engine.dispose()
    output = Path(".test-runs/dashboard-vision-live.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in report:
        print(json.dumps(item, ensure_ascii=False))
    return 0 if all(item["passed"] for item in report) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
