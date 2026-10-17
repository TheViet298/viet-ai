"""Run 10 live traces through VinFast AI Agent with OpenAI and push to Langfuse Cloud."""
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(ROOT / '.env', override=False)
os.environ['LANGFUSE_TRACING_ENABLED'] = 'true'
os.environ['LANGFUSE_TRACING_ENVIRONMENT'] = 'live-demonstration'

CASES = [
    {
        "id": "CASE-01",
        "title": "Làm quen & Giới thiệu xe",
        "message": "Xin chào! Tôi mới mua xe VinFast VF8, trợ lý có thể giúp tôi làm quen với các tính năng cơ bản không?",
        "expected_intent": "General/Onboarding"
    },
    {
        "id": "CASE-02",
        "title": "Chính sách bảo hành pin VF8",
        "message": "Chính sách bảo hành bộ pin cao áp của xe VinFast VF8 là bao nhiêu năm hoặc bao nhiêu km?",
        "expected_intent": "Warranty/Policy"
    },
    {
        "id": "CASE-03",
        "title": "Khẩn cấp: Bốc khói khoang pin",
        "message": "Xe VF8 của tôi đang bốc khói nghi ngút ở khoang pin dưới gầm xe, cần hỗ trợ gấp!",
        "expected_intent": "Emergency/Critical"
    },
    {
        "id": "CASE-04",
        "title": "Khẩn cấp: Mất phanh đột ngột",
        "message": "Xe VF6 đang chạy với tốc độ 50km/h thì bị mất trợ lực phanh, bàn đạp cứng đơ!",
        "expected_intent": "Emergency/Critical"
    },
    {
        "id": "CASE-05",
        "title": "Trụ sạc báo đèn đỏ không nhận sạc",
        "message": "Tôi cắm súng sạc tại trạm sạc công cộng nhưng trụ sạc liên tục nhấp nháy đèn đỏ và xe không vào điện.",
        "expected_intent": "Charging/Troubleshoot"
    },
    {
        "id": "CASE-06",
        "title": "Kẹt súng sạc tại trụ",
        "message": "Súng sạc tại trụ sạc nhanh DC bị kẹt cứng ở cổng sạc đuôi xe VF5, không thể rút ra được.",
        "expected_intent": "Charging/Technical"
    },
    {
        "id": "CASE-07",
        "title": "Cảnh báo rùa vàng trên cao tốc",
        "message": "Xe VF8 đang chạy trên cao tốc bỗng nhiên hiện biểu tượng rùa vàng trên taplo và bị giảm công suất.",
        "expected_intent": "Safety/Warning"
    },
    {
        "id": "CASE-08",
        "title": "Màn hình giải trí bị treo đen",
        "message": "Màn hình cảm ứng giải trí trung tâm của xe VF7 bị đen thui và đơ, làm sao để khởi động lại?",
        "expected_intent": "Infotainment/Support"
    },
    {
        "id": "CASE-09",
        "title": "Tìm trạm sạc gần nhất",
        "message": "Tôi đang gần khu vực Cầu Giấy, Hà Nội. Hãy chỉ cho tôi trạm sạc VinFast gần nhất đang hoạt động.",
        "expected_intent": "ServicePoint/Location"
    },
    {
        "id": "CASE-10",
        "title": "Lịch bảo dưỡng định kỳ",
        "message": "Lịch bảo dưỡng định kỳ lần đầu cho xe điện VinFast VF5 là bao nhiêu km và chi phí khoảng bao nhiêu?",
        "expected_intent": "Maintenance/Schedule"
    }
]


async def get_project_id() -> str | None:
    import httpx
    public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
    secret_key = os.getenv('LANGFUSE_SECRET_KEY')
    base_url = os.getenv('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com').rstrip('/')
    if not public_key or not secret_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=15, auth=(public_key, secret_key)) as client:
            resp = await client.get(f"{base_url}/api/public/projects")
            if resp.status_code == 200:
                projects = resp.json().get('data', [])
                if projects:
                    return projects[0].get('id')
    except Exception as e:
        print(f"Warning: could not fetch project_id: {e}")
    return None


async def run_traces():
    from src.main import app
    from src.config import get_settings
    from src.services import observability as obs
    import httpx

    settings = get_settings()
    project_id = await get_project_id() or "cmuzofl6c02a5ad0ixpvdmca1"
    run_id = f"demo-10-traces-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    print("=" * 70)
    print(f"LANGFUSE LIVE TRACING: CHẠY 10 TRACES VỚI MODEL THẬT ({settings.model_name})")
    print(f"Project ID: {project_id}")
    print(f"Run ID: {run_id}")
    print("=" * 70)

    from src.db import SessionLocal
    from src.models.db_models import User
    from src.services.auth import create_token
    from scripts.check_langfuse_matrix import seed_validation_user

    results = []

    async with app.router.lifespan_context(app):
        if not obs.is_langfuse_available():
            raise RuntimeError("Langfuse client is not available. Please check credentials.")

        with SessionLocal() as db:
            if not db.get(User, "lf-synthetic-user"):
                seed_validation_user(db)
        demo_token = create_token("lf-synthetic-user", "CUSTOMER")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://vinfast-agent") as client:
            for idx, case in enumerate(CASES, start=1):
                case_id = case["id"]
                title = case["title"]
                message = case["message"]
                session_id = f"{run_id}-{case_id}"

                print(f"\n[{idx}/10] {case_id}: {title}...")
                start_time = time.monotonic()

                with obs.validation_context(run_id, case_id):
                    with obs.observation(f"p142.live.{case_id}", metadata={"case_id": case_id, "title": title}) as root:
                        trace_id = obs.current_trace_id()
                        obs.update_observation(root, input={"message": message, "title": title})

                        try:
                            payload = {
                                "session_id": session_id,
                                "message": message,
                            }
                            for m in ("VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "e34"):
                                if m in message:
                                    payload["client_context"] = {"vehicle_model": m}
                                    break

                            response = await client.post(
                                "/api/v1/chat",
                                json=payload,
                                headers={"Authorization": f"Bearer {demo_token}"}
                            )
                            status_code = response.status_code
                            data = response.json() if status_code == 200 else {}
                            error_detail = None if status_code == 200 else response.text
                        except Exception as exc:
                            status_code = 500
                            data = {}
                            error_detail = str(exc)

                        elapsed = round(time.monotonic() - start_time, 2)
                        obs.update_observation(root, output=data, metadata={"status_code": status_code, "elapsed_s": elapsed})

                        # Ghi nhận Score vào Langfuse Trace
                        if trace_id:
                            obs.score_trace("agent_latency_s", float(elapsed), trace_id=trace_id)
                            obs.score_trace("http_success", 1.0 if status_code == 200 else 0.0, trace_id=trace_id)
                            if data.get("is_safety_trigger"):
                                obs.score_trace("safety_triggered", 1.0, trace_id=trace_id, comment="Emergency trigger recognized")

                reply_snippet = (data.get("response") or data.get("reply") or error_detail or "")[:120].replace("\n", " ")
                trace_url = f"https://cloud.langfuse.com/project/{project_id}/traces/{trace_id}" if trace_id else "N/A"

                result_entry = {
                    "case_id": case_id,
                    "title": title,
                    "status_code": status_code,
                    "duration_s": elapsed,
                    "trace_id": trace_id,
                    "trace_url": trace_url,
                    "reply": reply_snippet
                }
                results.append(result_entry)
                print(f"    ✓ Xong trong {elapsed}s | Trace: {trace_id}")
                print(f"    Phản hồi: {reply_snippet}...")

                # Nhịp nghỉ nhỏ giữa các request
                await asyncio.sleep(1)

        print("\n--> Đang đồng bộ (flush) tất cả traces lên Langfuse Cloud...")
        await obs.flush_observability(shutdown=True)

    print("\n" + "=" * 70)
    print("HOÀN THÀNH 10 TRACES THỰC TẾ TRÊN LANGFUSE!")
    print("=" * 70)
    print("\nDANH SÁCH 10 TRACES VỪA TẠO:")
    for r in results:
        print(f"- [{r['case_id']}] {r['title']} ({r['duration_s']}s): {r['trace_url']}")

    # Lưu kết quả ra file JSON
    out_file = ROOT / "tmp" / f"{run_id}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nĐã lưu kết quả chi tiết tại: {out_file}")
    return results, project_id


if __name__ == "__main__":
    asyncio.run(run_traces())
