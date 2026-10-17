"""Run multimodal test cases (Text Messages & Images) calling LLM and pushing to Langfuse Cloud."""
import asyncio
import io
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(ROOT / '.env', override=False)
os.environ['LANGFUSE_TRACING_ENABLED'] = 'true'
os.environ['LANGFUSE_TRACING_ENVIRONMENT'] = 'multimodal-live-eval'

from PIL import Image, ImageDraw
from scripts.check_langfuse_matrix import synthetic_image


def generate_image_fixture(variant: str) -> bytes:
    """Generate synthetic image for dashboard warning or exterior vehicle."""
    if variant == "low_pressure":
        return synthetic_image("dashboard")
    elif variant == "generic_vehicle":
        return synthetic_image("exterior")
    elif variant == "sensor_fault":
        data = synthetic_image("dashboard")
        img = Image.open(io.BytesIO(data)).convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.rectangle((100, 440, 870, 530), fill="#080a0d")
        draw.text((160, 465), "Tire pressure sensor fault", fill="#ffcd00", font_size=34)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    elif variant == "no_vehicle":
        data = synthetic_image("exterior")
        img = Image.open(io.BytesIO(data)).convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, 960, 640), fill="#e4e8ef")
        draw.rectangle((260, 180, 700, 460), fill="#4b5563")
        draw.text((270, 90), "SYNTHETIC - NO VEHICLE", fill="#111827", font_size=28)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    else:
        return synthetic_image("dashboard")


CASES = [
    # --- PHẦN 1: TIN NHẮN VĂN BẢN (TEXT / CHAT LLM) ---
    {
        "id": "CASE-TXT-01",
        "kind": "chat",
        "category": "Onboarding & Giới thiệu",
        "message": "Xin chào! Tôi mới mua xe VinFast VF8, trợ lý có thể giúp tôi làm quen với các tính năng cơ bản không?",
        "vehicle_model": "VF8"
    },
    {
        "id": "CASE-TXT-02",
        "kind": "chat",
        "category": "Chính sách & RAG FAQ",
        "message": "Chính sách bảo hành bộ pin cao áp của xe VinFast VF8 là bao nhiêu năm hoặc bao nhiêu km?",
        "vehicle_model": "VF8"
    },
    {
        "id": "CASE-TXT-03",
        "kind": "chat",
        "category": "Khẩn cấp (Hard Safety)",
        "message": "Xe VF8 của tôi đang bốc khói nghi ngút ở khoang pin dưới gầm xe, cần hỗ trợ gấp!",
        "vehicle_model": "VF8"
    },
    {
        "id": "CASE-TXT-04",
        "kind": "chat",
        "category": "Khẩn cấp (Mất trợ lực phanh)",
        "message": "Xe VF6 đang chạy tốc độ 60km/h thì bị mất trợ lực phanh khẩn cấp!",
        "vehicle_model": "VF6"
    },
    {
        "id": "CASE-TXT-05",
        "kind": "chat",
        "category": "Sự cố sạc & Hướng dẫn",
        "message": "Súng sạc DC tại trụ sạc nhanh bị kẹt ở cổng sạc đuôi xe VF5, không thể rút ra được.",
        "vehicle_model": "VF5"
    },
    {
        "id": "CASE-TXT-06",
        "kind": "chat",
        "category": "Dịch vụ & Vị trí trạm sạc",
        "message": "Tôi đang gần khu vực Cầu Giấy, Hà Nội. Hãy chỉ cho tôi trạm sạc VinFast gần nhất đang hoạt động.",
        "vehicle_model": None
    },

    # --- PHẦN 2: HÌNH ẢNH (MULTIMODAL VISION LLM) ---
    {
        "id": "CASE-IMG-01",
        "kind": "upload",
        "category": "Ảnh táp-lô: Áp suất lốp thấp",
        "image_kind": "dashboard",
        "variant": "low_pressure",
        "expected_signal": "low_pressure"
    },
    {
        "id": "CASE-IMG-02",
        "kind": "upload",
        "category": "Ảnh táp-lô: Lỗi cảm biến TPMS",
        "image_kind": "dashboard",
        "variant": "sensor_fault",
        "expected_signal": "sensor_fault"
    },
    {
        "id": "CASE-IMG-03",
        "kind": "upload",
        "category": "Ảnh ngoại thất: Nhận diện xe & hư hại",
        "image_kind": "exterior",
        "variant": "generic_vehicle",
        "expected_signal": "exterior_analysis"
    },
    {
        "id": "CASE-IMG-04",
        "kind": "upload",
        "category": "Ảnh âm tính: Không có xe (Anti-hallucination)",
        "image_kind": "exterior",
        "variant": "no_vehicle",
        "expected_signal": "no_vehicle"
    }
]


async def get_project_id() -> str:
    import httpx
    public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
    secret_key = os.getenv('LANGFUSE_SECRET_KEY')
    base_url = os.getenv('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com').rstrip('/')
    try:
        async with httpx.AsyncClient(timeout=15, auth=(public_key, secret_key)) as client:
            resp = await client.get(f"{base_url}/api/public/projects")
            if resp.status_code == 200:
                projects = resp.json().get('data', [])
                if projects:
                    return projects[0].get('id')
    except Exception:
        pass
    return "cmuzofl6c02a5ad0ixpvdmca1"


async def run_multimodal():
    from src.main import app
    from src.config import get_settings
    from src.db import SessionLocal
    from src.models.db_models import User
    from src.services.auth import create_token
    from src.services import observability as obs
    from scripts.check_langfuse_matrix import seed_validation_user
    import httpx

    settings = get_settings()
    project_id = await get_project_id()
    run_id = f"demo-multimodal-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    print("=" * 75)
    print("LANGFUSE MULTIMODAL EVAL: CHẠY TEST CASE TỪ TIN NHẮN ĐẾN HÌNH ẢNH")
    print(f"Chat Model: {settings.model_name} | Vision Model: {settings.vision_model}")
    print(f"Project ID: {project_id}")
    print(f"Run ID: {run_id}")
    print("=" * 75)

    results = []

    async with app.router.lifespan_context(app):
        if not obs.is_langfuse_available():
            raise RuntimeError("Langfuse client is not available. Please check credentials.")

        with SessionLocal() as db:
            if not db.query(User).filter_by(username="lf-synthetic-user").first():
                seed_validation_user(db)
        token = create_token("lf-synthetic-user", "CUSTOMER")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://vinfast-agent") as client:
            for idx, case in enumerate(CASES, start=1):
                case_id = case["id"]
                category = case["category"]
                kind = case["kind"]
                session_id = f"{run_id}-{case_id}"

                print(f"\n[{idx}/10] [{kind.upper()}] {case_id}: {category}...")
                start_time = time.monotonic()

                with obs.validation_context(run_id, case_id):
                    with obs.observation(f"p142.{kind}.{case_id}", metadata={"case_id": case_id, "kind": kind, "category": category}) as root:
                        trace_id = obs.current_trace_id()

                        if kind == "chat":
                            message = case["message"]
                            obs.update_observation(root, input={"message": message, "category": category})

                            payload = {"session_id": session_id, "message": message}
                            if case.get("vehicle_model"):
                                payload["client_context"] = {"vehicle_model": case["vehicle_model"]}

                            try:
                                resp = await client.post("/api/v1/chat", json=payload, headers={"Authorization": f"Bearer {token}"})
                                status = resp.status_code
                                data = resp.json() if status == 200 else {}
                            except Exception as e:
                                status, data = 500, {"error": str(e)}

                            elapsed = round(time.monotonic() - start_time, 2)
                            obs.update_observation(root, output=data, metadata={"status_code": status, "elapsed_s": elapsed})

                            # Scores
                            if trace_id:
                                obs.score_trace("call_latency_s", float(elapsed), trace_id=trace_id)
                                obs.score_trace("call_success", 1.0 if status == 200 else 0.0, trace_id=trace_id)
                                if data.get("is_safety_trigger"):
                                    obs.score_trace("safety_triggered", 1.0, trace_id=trace_id)

                            reply_preview = (data.get("response") or data.get("reply") or str(data))[:110].replace("\n", " ")
                            detail_info = f"Chat Response: {reply_preview}..."

                        else:
                            # KIND == 'upload' (Vision LLM)
                            image_kind = case["image_kind"]
                            variant = case["variant"]
                            image_bytes = generate_image_fixture(variant)

                            obs.update_observation(root, input={"image_kind": image_kind, "variant": variant, "size_bytes": len(image_bytes)})

                            try:
                                resp = await client.post(
                                    "/api/v1/customer/attachments",
                                    headers={"Authorization": f"Bearer {token}"},
                                    data={"image_kind": image_kind},
                                    files={"file": (f"{case_id}.png", image_bytes, "image/png")}
                                )
                                status = resp.status_code
                                data = resp.json() if status == 200 else {}
                            except Exception as e:
                                status, data = 500, {"error": str(e)}

                            elapsed = round(time.monotonic() - start_time, 2)
                            signals = data.get("data", {}).get("detected_signals", {})
                            obs.update_observation(root, output=signals, metadata={"status_code": status, "elapsed_s": elapsed})

                            # Scores
                            if trace_id:
                                obs.score_trace("call_latency_s", float(elapsed), trace_id=trace_id)
                                obs.score_trace("vision_success", 1.0 if status == 200 and not signals.get("analysis_error") else 0.0, trace_id=trace_id)
                                if signals.get("ocr_text"):
                                    obs.score_trace("ocr_detected", 1.0, trace_id=trace_id)

                            ocr = signals.get("ocr_text", "").replace("\n", " ")[:60]
                            symptoms = signals.get("symptom_keys", [])
                            vehicle_res = signals.get("vehicle_evidence", {}).get("status") or signals.get("evidence_type")
                            detail_info = f"OCR: '{ocr}' | Symptoms: {symptoms} | Vision: {vehicle_res}"

                trace_url = f"https://cloud.langfuse.com/project/{project_id}/traces/{trace_id}" if trace_id else "N/A"
                print(f"    ✓ Xong trong {elapsed}s | Trace: {trace_id}")
                print(f"    {detail_info}")

                results.append({
                    "id": case_id,
                    "kind": kind,
                    "category": category,
                    "status_code": status,
                    "duration_s": elapsed,
                    "trace_id": trace_id,
                    "trace_url": trace_url,
                    "detail": detail_info
                })

                await asyncio.sleep(1)

        print("\n--> Đang đồng bộ toàn bộ Traces & Spans lên Langfuse Cloud...")
        await obs.flush_observability(shutdown=True)

    print("\n" + "=" * 75)
    print("HOÀN THÀNH TẤT CẢ TEST CASES (TIN NHẮN & HÌNH ẢNH) TRÊN LANGFUSE!")
    print("=" * 75)
    for r in results:
        print(f"- [{r['id']}] ({r['kind'].upper()}) {r['category']} ({r['duration_s']}s): {r['trace_url']}")

    # Save output
    out_file = ROOT / "tmp" / f"{run_id}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã lưu báo cáo tại: {out_file}")
    return results, project_id


if __name__ == "__main__":
    asyncio.run(run_multimodal())
