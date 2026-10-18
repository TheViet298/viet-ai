"""A location action is separate from the four business intents. No GPS in LLM context."""

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.services.agent_llm import structured_call


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold()).replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if not unicodedata.combining(c))).strip()


class LocationClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    find_nearby: bool
    category: Literal["CHARGING_STATION", "SHOWROOM", "SERVICE_WORKSHOP", "OTHER", "ALL"]
    confidence: float = Field(ge=0, le=1)


AREAS = {
    "ha noi": "Hà Nội", "hanoi": "Hà Nội", "ho chi minh": "TP. Hồ Chí Minh",
    "tp hcm": "TP. Hồ Chí Minh", "tphcm": "TP. Hồ Chí Minh", "sai gon": "TP. Hồ Chí Minh",
    "da nang": "Đà Nẵng", "hue": "Huế", "long thanh": "Cao tốc Long Thành",
}
LABELS = {"CHARGING_STATION": "trạm sạc", "SHOWROOM": "showroom",
          "SERVICE_WORKSHOP": "xưởng dịch vụ", "OTHER": "điểm hỗ trợ", "ALL": "địa điểm"}


async def classify_location_request(text: str, previous: dict | None = None, vehicle_model: str | None = None) -> dict | None:
    value = normalize(text)
    if re.search(r"\b(khong (?:can |muon )?tim|dung tim|thoi bo|bo qua|huy tim)\b", value):
        return None
    category = None
    for candidate, pattern in (
        ("SHOWROOM", r"showroom|dai ly|phong trung bay"),
        ("SERVICE_WORKSHOP", r"xuong|cho sua xe|noi sua xe|trung tam dich vu|cho bao duong"),
        ("CHARGING_STATION", r"tram sac|tru sac|cho sac|noi sac|diem sac"),
        ("OTHER", r"diem cuu ho"),
    ):
        if re.search(pattern, value):
            category = candidate
            break
    nearby = bool(re.search(r"gan (?:day|toi|nhat|minh|em)|quanh (?:day|toi)|xung quanh", value))
    seeking = bool(re.search(r"\b(tim|chi duong|o dau|cho nao|danh sach|co .+ khong|can den|muon den)\b", value))
    faq = bool(re.search(r"la gi|bao lau|cach sac|huong dan sac|chinh sach|gia sac|phi sac|quy trinh|tinh phi|bao hanh", value))
    if not category and re.search(r"quan an|nha hang|khach san|benh vien", value):
        return None
    if re.search(r"bi hong|bao loi|khong hoat dong|khong sac duoc|ket sung|khong vao dien", value) and not re.search(r"\b(tim|chi duong|noi khac|cho khac)\b", value):
        return None
    area = next((label for alias, label in AREAS.items() if re.search(r"\b(?:o|tai|quanh|khu vuc) " + re.escape(alias) + r"\b", value)), None)
    contextual = previous and (nearby or re.search(r"\b(con .+ thi sao|cho khac|noi khac|gan hon|o day|chi duong|cho dau tien)\b", value))
    if (faq or "tim hieu" in value) and not nearby:
        return None
    if contextual:
        category = category or previous["category"]
        area = area or (previous.get("area_text") if not nearby else None)
    elif not (category and (nearby or seeking or area)):
        # Only consider an online fallback for a location-shaped utterance. FAQ is deterministic.
        if not (nearby or (category and not faq)):
            return None
        result = await structured_call({"session_id": "nearby-classification", "messages": [
            {"role": "user", "content": text}], "latest_user_message": text, "query": text}, "nearby_intent", LocationClassification)
        if result and result.find_nearby and result.confidence >= 0.9:
            category = result.category
        elif nearby and not category and not re.search(r"quan an|nha hang|khach san|benh vien", value):
            category = "ALL"
        else:
            return None
    vehicle = "TWO_WHEELER" if re.search(r"xe may|xe dien hai banh|scooter", value) else (
        "CAR" if re.search(r"o to|xe hoi|\bvf\s*\d", value) else (previous or {}).get("vehicle_type", "CAR"))
    return {"category": category, "vehicle_type": vehicle, "area_text": area,
            "requires_location": not bool(area),
            "reason": f"Tìm {LABELS[category]} {'ô tô' if vehicle == 'CAR' else 'xe máy điện'} gần bạn."}
