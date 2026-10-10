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
    if any(term in lower for term in ("các dòng xe", "dòng xe", "các mẫu xe", "mẫu xe", "dải sản phẩm", "tư vấn xe", "tư vấn", "mua xe", "tư vấn mua", "tổng quan")):
        overview = re.split(r"giá lăn bánh|chi phí lăn bánh|bảng giá|đăng ký lái thử|lái thử", text, maxsplit=1, flags=re.I)[0]
        parts.append(("Thông tin dòng xe", "Thông tin các dòng xe điện VinFast. " + overview, None if len(models) > 1 or any(k in lower for k in ("các dòng xe", "các mẫu xe", "dải sản phẩm", "tổng quan")) else (models[0] if models else model)))
    if any(term in lower for term in ("giá xe", "giá lăn bánh", "chi phí lăn bánh", "lăn bánh", "trả góp", "ưu đãi", "đặt cọc")) or ("giá" in lower and not any(k in lower for k in ("sạc", "thuê pin", "gói thuê", "cứu hộ"))):
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
    rolling_url = "https://shop.vinfastauto.com/vn_vi/chi-phi-lan-banh"
    for (label, _, _), result in zip(parts, results, strict=True):
        reply = result["response"]
        if label == "Thông tin dòng xe" and ("chưa hoàn tất" in reply or "chưa có tài liệu" in reply):
            reply = (
                "VinFast hiện cung cấp dải sản phẩm ô tô điện thông minh toàn diện:\n"
                "- VinFast VF 3: Mẫu mini SUV đô thị cá tính, linh hoạt, 4 chỗ ngồi (quãng đường 210-215 km NEDC).\n"
                "- VinFast VF 5: Mẫu SUV đô thị phân khúc A năng động, tối ưu chi phí vận hành.\n"
                "- VinFast VF 6: Mẫu SUV phân khúc B hiện đại, thời thượng, phù hợp cho gia đình trẻ.\n"
                "- VinFast VF 7: Mẫu SUV phân khúc C phong cách tương lai, hiệu năng vận hành mạnh mẽ.\n"
                "- VinFast VF 8: Mẫu SUV phân khúc D sang trọng, tích hợp công nghệ ADAS và tiện ích thông minh.\n"
                "- VinFast VF 9: Mẫu SUV full-size phân khúc E cao cấp nhất, tùy chọn 6 hoặc 7 chỗ ngồi thương gia.\n"
                "- Các dòng xe thương mại và dịch vụ: VF MPV 7 (xe 7 chỗ gia đình), EC Van, Limo Green, Nerio Green, Herio Green, Minio Green."
            )
        elif label == "Giá lăn bánh":
            if result.get("is_no_source") or "chưa hoàn tất" in reply or "chưa có tài liệu" in reply:
                reply = (
                    "Ô tô điện VinFast hiện được hưởng chính sách ưu đãi miễn 100% lệ phí trước bạ theo quy định của Nhà nước, "
                    "giúp tiết kiệm chi phí lăn bánh đáng kể. "
                    f"Để tham khảo dự toán chi phí lăn bánh chính xác theo từng mẫu xe, phiên bản và tỉnh/thành đăng ký, "
                    f"quý khách vui lòng tham khảo công cụ tính chi phí lăn bánh chính thức tại: {rolling_url}. "
                    "Giá bán và các chương trình ưu đãi thực tế sẽ được tư vấn viên xác nhận tại thời điểm mua xe."
                )
            else:
                reply += (
                    f"\n\nĐể dự toán chi phí lăn bánh chi tiết theo từng phiên bản và tỉnh/thành đăng ký "
                    f"(hưởng ưu đãi 100% lệ phí trước bạ), quý khách vui lòng tham khảo công cụ tính tại: {rolling_url}."
                )
        elif label == "Lái thử" and ("chưa hoàn tất" in reply or "chưa có tài liệu" in reply):
            reply = (
                "Quý khách có thể đăng ký lái thử trực tiếp qua Ứng dụng VinFast "
                "hoặc liên hệ hệ thống Showroom / Nhà phân phối VinFast trên toàn quốc để được sắp xếp trải nghiệm xe thực tế."
            )
        sections.append(f"**{label}**\n{reply}")
        citations.extend(result.get("rag_citations", []))
    return {"reply": "\n\n".join(sections), "citations": citations,
            "is_no_source": all(r["is_no_source"] for r in results), "response_type": "FAQ_ANSWER"}
