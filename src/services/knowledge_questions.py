"""Bounded decomposition of sales questions; every part uses verified evidence."""
import asyncio
import re
import time

from src.agents.guardrails import sanitize_pii
from src.agents.nodes.rag_node import rag_node
from src.config import get_settings


def explicit_models(text: str) -> list[str]:
    return list(dict.fromkeys("VF" + m.upper() for m in re.findall(r"\bvf\s*(e34|[356789])\b", text, re.I)))


def sales_parts(text: str, model: str | None) -> list[tuple[str, str, str | None]]:
    lower = text.casefold()
    models = explicit_models(text)
    if not models and model:
        models = [model]
    # The model in the test-drive clause must not narrow the whole lineup.
    drive = re.search(r"(?:lái thử|chạy thử|trải nghiệm xe).*?\bvf\s*(e34|[356789])\b", lower)
    drive_model = "VF" + drive.group(1).upper() if drive else (models[0] if len(models) == 1 else model)
    parts = []
    if any(term in lower for term in ("các dòng xe", "dòng xe", "tư vấn xe", "mua xe", "tư vấn mua")):
        overview = re.split(r"giá lăn bánh|chi phí lăn bánh|bảng giá|đăng ký lái thử|lái thử", text, maxsplit=1, flags=re.I)[0]
        parts.append(("Thông tin dòng xe", "Thông tin các dòng xe điện VinFast. " + overview, None if len(models) > 1 or "các dòng xe" in lower else (models[0] if models else model)))
    if any(term in lower for term in ("giá", "trả góp", "ưu đãi", "đặt cọc")):
        parts.append(("Giá lăn bánh", "Giá xe và chi phí lăn bánh VinFast " + " ".join(models), models[0] if len(models) == 1 else None))
    if any(term in lower for term in ("lái thử", "chạy thử", "trải nghiệm xe")):
        parts.append(("Lái thử", f"Đăng ký lái thử xe VinFast {drive_model or ''}, hình thức và điều kiện đăng ký.", drive_model))
    return parts


async def answer_sales_question(text: str, model: str | None, session_id: str) -> dict:
    text = sanitize_pii(text)[0]
    parts = sales_parts(text, model)
    deadline = time.monotonic() + get_settings().agent_turn_timeout_s
    results = await asyncio.gather(*(rag_node({
        "latest_user_message": query, "vehicle_model": vehicle,
        "confidence_score": .9, "session_id": session_id, "turn": 0,
        "llm_budget": {"deadline": deadline, "attempts": 0},
    }) for _, query, vehicle in parts))
    sections, citations = [], []
    for (label, _, _), result in zip(parts, results, strict=True):
        reply = result["response"]
        if label == "Giá lăn bánh":
            reply += "\nĐể tính giá lăn bánh cụ thể, cần mẫu xe, phiên bản và tỉnh/thành đăng ký; giá và ưu đãi cần được xác nhận tại thời điểm mua."
        sections.append(f"**{label}**\n{reply}")
        citations.extend(result.get("rag_citations", []))
    return {"reply": "\n\n".join(sections), "citations": citations,
            "is_no_source": all(r["is_no_source"] for r in results), "response_type": "FAQ_ANSWER"}
