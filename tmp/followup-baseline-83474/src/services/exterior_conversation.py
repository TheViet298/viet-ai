"""Describe visible exterior damage and offer customer-selected assistance."""
import time

from src.agents.nodes.rag_node import rag_node
from src.config import get_settings
from src.services.dashboard_conversation import INCIDENT_CHOICE
from src.services.dashboard_warning_service import normalize

REPAIR_CHOICE = "Tư vấn sửa chữa và bảo hành"
EXTERIOR_CHOICES = [INCIDENT_CHOICE, REPAIR_CHOICE]


def exterior_question(text: str) -> bool:
    value = normalize(text)
    if any(term in value for term in ("bao hanh pin", "bao hanh ac quy", "bao hanh bao lau", "thoi han bao hanh")):
        return False
    return any(term in value for term in (
        "trong anh", "hu hai", "hu hong", "sua chua", "bao hanh", "bao hiem", "mop", "bien dang",
    ))


def describe_exterior(signals: list[dict]) -> str:
    model = next((s.get("vehicle_model") for s in signals if s.get("vehicle_model")), None)
    opening = (f"Em nhận diện sơ bộ mẫu xe **{model}**; vui lòng xác nhận giúp em."
               if model else "Em chưa xác định chắc chắn mẫu xe trong ảnh.")
    damages = [damage for signal in signals for damage in signal.get("exterior_observation", {}).get("damages", [])
               if damage.get("confidence", 0) >= .8]
    lines = [f"- **{d['part']}** ({d['location']}): {d['description'].rstrip('. ')}." for d in damages]
    return (opening + "\n\n**Dấu hiệu hư hại quan sát được:**\n" + "\n".join(lines)
            + "\n\nẢnh chưa đủ để xác định nguyên nhân, tình trạng pin/hệ thống bên trong hoặc khả năng vận hành an toàn của xe.")


async def warranty_answer(model: str | None, session_id: str, text: str) -> tuple[str, list[dict]]:
    query = ("Bảo hành ô tô VinFast: hư hỏng do tai nạn, ngoại vật tác động vào xe có thuộc phạm vi bảo hành không?"
             if text == REPAIR_CHOICE else text)
    result = await rag_node({
        "latest_user_message": query,
        "vehicle_model": model, "session_id": session_id, "confidence_score": .9, "turn": 0,
        "llm_budget": {"deadline": time.monotonic() + get_settings().agent_turn_timeout_s, "attempts": 0},
    })
    if result.get("is_no_source"):
        return "Em chưa tra cứu được tài liệu chính thức đủ để trả lời. Vui lòng thử lại hoặc liên hệ xưởng dịch vụ để kiểm tra.", []
    return result["response"], result.get("rag_citations", [])


async def repair_advice(signals: list[dict], text: str, session_id: str) -> tuple[str, list[dict]]:
    reply = ("**Hướng dẫn sửa chữa:** cần đưa xe đến xưởng dịch vụ để kiểm tra trực tiếp các bộ phận được nhận diện và xác định phương án sửa chữa. "
              "Nếu xe biến dạng nhiều hoặc vận hành bất thường, hãy liên hệ cứu hộ để vận chuyển xe thay vì tự lái.")
    if "bao hiem" in normalize(text):
        return reply + "\n\nHệ thống chưa có dữ liệu chính sách bảo hiểm; vui lòng liên hệ đơn vị bảo hiểm để kiểm tra hợp đồng và quyền lợi.", []
    model = next((s.get("vehicle_model") for s in signals if s.get("vehicle_model")), None)
    policy, citations = await warranty_answer(model, session_id, text)
    reply += ("\n\n**Thông tin bảo hành:**\n" + policy
              + "\n\nChưa thể xác nhận xe được bảo hành chỉ từ ảnh; xưởng cần kiểm tra nguyên nhân và điều kiện áp dụng cho xe.")
    return reply, citations
