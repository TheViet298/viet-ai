"""Run test cases covering all 3 models: gemini-2.5-flash-lite, gpt-6-luna, and gpt-4o-mini."""
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
os.environ['LANGFUSE_TRACING_ENVIRONMENT'] = 'three-models-eval'

from PIL import Image, ImageDraw
from scripts.check_langfuse_matrix import synthetic_image


def generate_image(variant: str) -> bytes:
    if variant == "low_pressure":
        return synthetic_image("dashboard")
    elif variant == "sensor_fault":
        data = synthetic_image("dashboard")
        img = Image.open(io.BytesIO(data)).convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.rectangle((100, 440, 870, 530), fill="#080a0d")
        draw.text((160, 465), "Tire pressure sensor fault", fill="#ffcd00", font_size=34)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    elif variant == "exterior":
        return synthetic_image("exterior")
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
    return synthetic_image("dashboard")


CASES = [
    # =========================================================================
    # NHÓM 1: gemini-2.5-flash-lite (Chat Normalization / Sửa lỗi chính tả, viết tắt)
    # =========================================================================
    {
        "id": "M1-GEMINI-NORM-01",
        "model_target": "gemini-2.5-flash-lite",
        "kind": "normalization",
        "title": "Chuẩn hóa viết tắt sạc pin (k nhan sac, giup mik)",
        "raw_text": "xe mik k nhan sac o tram sac, giup mik vs",
    },
    {
        "id": "M1-GEMINI-NORM-02",
        "model_target": "gemini-2.5-flash-lite",
        "kind": "normalization",
        "title": "Chuẩn hóa viết tắt khởi động xe (k khoi dong dc)",
        "raw_text": "xe vf e34 k khoi dong dc, man hinh toi thui",
    },
    {
        "id": "M1-GEMINI-NORM-03",
        "model_target": "gemini-2.5-flash-lite",
        "kind": "normalization",
        "title": "Chuẩn hóa câu hỏi bảo dưỡng (ntn, bth)",
        "raw_text": "lich bao duong xe vf5 ntn vay ad, xe van chay bth",
    },

    # =========================================================================
    # NHÓM 2: gpt-6-luna (Multimodal Vision LLM / Táp-lô, OCR, Ngoại thất xe)
    # =========================================================================
    {
        "id": "M2-GPT6LUNA-VIS-01",
        "model_target": "gpt-6-luna",
        "kind": "vision",
        "image_kind": "dashboard",
        "variant": "low_pressure",
        "title": "Ảnh táp-lô: Nhận diện OCR cảnh báo áp suất lốp thấp",
    },
    {
        "id": "M2-GPT6LUNA-VIS-02",
        "model_target": "gpt-6-luna",
        "kind": "vision",
        "image_kind": "dashboard",
        "variant": "sensor_fault",
        "title": "Ảnh táp-lô: Nhận diện lỗi cảm biến áp suất TPMS",
    },
    {
        "id": "M2-GPT6LUNA-VIS-03",
        "model_target": "gpt-6-luna",
        "kind": "vision",
        "image_kind": "exterior",
        "variant": "exterior",
        "title": "Ảnh ngoại thất: Phân tích thân vỏ & nhận diện dòng xe",
    },
    {
        "id": "M2-GPT6LUNA-VIS-04",
        "model_target": "gpt-6-luna",
        "kind": "vision",
        "image_kind": "exterior",
        "variant": "no_vehicle",
        "title": "Ảnh âm tính: Chống ảo giác nhận diện khi không có xe",
    },

    # =========================================================================
    # NHÓM 3: gpt-4o-mini (Agent Core / Reasoning, Triage & RAG)
    # =========================================================================
    {
        "id": "M3-GPT4OMINI-CHAT-01",
        "model_target": "gpt-4o-mini",
        "kind": "chat",
        "title": "Sự cố khẩn cấp: Bốc khói khoang pin (Hard Safety)",
        "message": "Xe VF8 của tôi đang bốc khói nghi ngút ở khoang pin dưới gầm xe, cần cứu hộ gấp!",
        "vehicle_model": "VF8",
    },
    {
        "id": "M3-GPT4OMINI-CHAT-02",
        "model_target": "gpt-4o-mini",
        "kind": "chat",
        "title": "Tra cứu chính sách bảo hành pin VF8 (RAG FAQ)",
        "message": "Chính sách bảo hành bộ pin cao áp của xe VinFast VF8 là bao nhiêu năm hoặc bao nhiêu km?",
        "vehicle_model": "VF8",
    },
    {
        "id": "M3-GPT4OMINI-CHAT-03",
        "model_target": "gpt-4o-mini",
        "kind": "chat",
        "title": "Kẹt súng sạc DC: Hướng dẫn kỹ thuật tháo chốt",
        "message": "Súng sạc DC tại trụ sạc nhanh bị kẹt ở cổng sạc đuôi xe VF5, không thể rút ra được.",
        "vehicle_model": "VF5",
    },
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


async def run_all():
    from src.main import app
    from src.config import get_settings
    from src.db import SessionLocal
    from src.models.db_models import User
    from src.services.auth import create_token
    from src.services import observability as obs
    from src.services.llm import get_normalization_llm
    from scripts.check_langfuse_matrix import seed_validation_user
    import httpx

    settings = get_settings()
    project_id = await get_project_id()
    run_id = f"eval-3models-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    print("=" * 80)
    print("LANGFUSE EVALUATION: KIỂM THỬ ĐỒNG THỜI 3 DÒNG MÔ HÌNH")
    print("1. gemini-2.5-flash-lite  --> Chuẩn hóa tin nhắn, tiếng Việt viết tắt")
    print("2. gpt-6-luna             --> Multimodal Vision (Táp-lô, OCR, Ngoại thất)")
    print("3. gpt-4o-mini            --> Agent suy luận hội thoại, RAG & Triage")
    print(f"Project ID: {project_id}")
    print(f"Run ID: {run_id}")
    print("=" * 80)

    results = []

    async with app.router.lifespan_context(app):
        if not obs.is_langfuse_available():
            raise RuntimeError("Langfuse client is not available.")

        with SessionLocal() as db:
            if not db.query(User).filter_by(username="lf-synthetic-user").first():
                seed_validation_user(db)
        token = create_token("lf-synthetic-user", "CUSTOMER")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://vinfast-agent") as client:
            for idx, case in enumerate(CASES, start=1):
                case_id = case["id"]
                model_target = case["model_target"]
                kind = case["kind"]
                title = case["title"]

                print(f"\n[{idx}/10] [{model_target}] {case_id}: {title}...")
                start_time = time.monotonic()

                with obs.validation_context(run_id, case_id):
                    with obs.observation(f"eval.{case_id}", metadata={"model_target": model_target, "kind": kind, "title": title}) as root:
                        trace_id = obs.current_trace_id()

                        # --- NHÓM 1: NORMALIZATION MODEL (gemini-2.5-flash-lite) ---
                        if kind == "normalization":
                            raw = case["raw_text"]
                            obs.update_observation(root, input={"raw_text": raw, "model": model_target})
                            prompt = (
                                "Bạn là bộ chuẩn hóa tin nhắn khách hàng VinFast. "
                                "Hãy chuyển đổi các từ viết tắt (k => không, mik => mình, vs => với, ntn => như thế nào, dc => được) "
                                f"về câu tiếng Việt chuẩn có dấu, giữ nguyên ý nghĩa.\nCâu gốc: '{raw}'\nCâu chuẩn hóa:"
                            )
                            norm_llm = get_normalization_llm()
                            with obs.observation("llm.normalization", as_type="generation", model=model_target,
                                                 metadata={"provider": "google", "layer": "normalization"}) as gen_span:
                                resp = await norm_llm.ainvoke(prompt)
                                cleaned = resp.content
                                if isinstance(cleaned, list) and cleaned and isinstance(cleaned[0], dict):
                                    cleaned = cleaned[0].get("text", "")
                                obs.update_observation(gen_span, output={"normalized_text": cleaned})

                            elapsed = round(time.monotonic() - start_time, 2)
                            obs.update_observation(root, output={"normalized_result": cleaned}, metadata={"elapsed_s": elapsed})
                            if trace_id:
                                obs.score_trace("model_call_success", 1.0, trace_id=trace_id)
                                obs.score_trace("latency_s", float(elapsed), trace_id=trace_id)
                            detail_info = f"Gốc: '{raw}' --> Chuẩn hóa: '{str(cleaned).strip()[:80]}'"

                        # --- NHÓM 2: VISION MODEL (gpt-6-luna) ---
                        elif kind == "vision":
                            image_kind = case["image_kind"]
                            variant = case["variant"]
                            img_bytes = generate_image(variant)
                            obs.update_observation(root, input={"image_kind": image_kind, "variant": variant, "model": model_target})

                            try:
                                resp = await client.post(
                                    "/api/v1/customer/attachments",
                                    headers={"Authorization": f"Bearer {token}"},
                                    data={"image_kind": image_kind},
                                    files={"file": (f"{case_id}.png", img_bytes, "image/png")}
                                )
                                status = resp.status_code
                                data = resp.json() if status == 200 else {}
                            except Exception as e:
                                status, data = 500, {"error": str(e)}

                            elapsed = round(time.monotonic() - start_time, 2)
                            signals = data.get("data", {}).get("detected_signals", {})
                            obs.update_observation(root, output=signals, metadata={"status_code": status, "elapsed_s": elapsed})

                            if trace_id:
                                obs.score_trace("model_call_success", 1.0 if status == 200 else 0.0, trace_id=trace_id)
                                obs.score_trace("latency_s", float(elapsed), trace_id=trace_id)

                            ocr = signals.get("ocr_text", "").replace("\n", " ")[:50]
                            symptoms = signals.get("symptom_keys", [])
                            detail_info = f"OCR: '{ocr}' | Triệu chứng: {symptoms} | Loại: {signals.get('evidence_type')}"

                        # --- NHÓM 3: CHAT / REASONING AGENT (gpt-4o-mini) ---
                        else:
                            message = case["message"]
                            obs.update_observation(root, input={"message": message, "model": model_target})
                            payload = {"session_id": f"{run_id}-{case_id}", "message": message}
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

                            if trace_id:
                                obs.score_trace("model_call_success", 1.0 if status == 200 else 0.0, trace_id=trace_id)
                                obs.score_trace("latency_s", float(elapsed), trace_id=trace_id)
                                if data.get("is_safety_trigger"):
                                    obs.score_trace("safety_triggered", 1.0, trace_id=trace_id)

                            reply = (data.get("response") or data.get("reply") or str(data))[:100].replace("\n", " ")
                            detail_info = f"Phản hồi: {reply}..."

                trace_url = f"https://cloud.langfuse.com/project/{project_id}/traces/{trace_id}" if trace_id else "N/A"
                print(f"    ✓ Hoàn thành trong {elapsed}s | Trace: {trace_id}")
                print(f"    {detail_info}")

                results.append({
                    "id": case_id,
                    "model": model_target,
                    "kind": kind,
                    "title": title,
                    "duration_s": elapsed,
                    "trace_id": trace_id,
                    "trace_url": trace_url,
                    "detail": detail_info
                })

                await asyncio.sleep(1)

        print("\n--> Đang đồng bộ toàn bộ Traces lên Langfuse Cloud...")
        await obs.flush_observability(shutdown=True)

    print("\n" + "=" * 80)
    print("HOÀN THÀNH TOÀN BỘ 10 TEST CASES VỚI CẢ 3 DÒNG MODEL!")
    print("=" * 80)
    for r in results:
        print(f"- [{r['model']}] {r['title']} ({r['duration_s']}s): {r['trace_url']}")

    out_file = ROOT / "tmp" / f"{run_id}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã lưu kết quả tại: {out_file}")
    return results, project_id


if __name__ == "__main__":
    asyncio.run(run_all())
