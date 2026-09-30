from __future__ import annotations

import os
import re
from typing import Any

from src.agents.guardrails import (
    evaluate_hard_safety,
    sanitize_pii,
    is_hitl_mandatory,
    EMERGENCY_SAFE_GUIDANCE,
    VINFAST_HOTLINE,
)
from src.services.rag_service import rag_service

SYSTEM_PROMPT_TEMPLATE = """Bạn là Trợ lý AI Dịch vụ Khách hàng VinFast (VinFast Virtual Service Assistant).
Nhiệm vụ của bạn là hỗ trợ chủ xe và khách hàng giải đáp thắc mắc về xe ô tô điện VinFast (bảo hành, trạm sạc, ứng dụng VinFast, sổ tay vận hành).

QUY TẮC CỐT LÕI (BẮT BUỘC TUÂN THỦ):
1. CHỈ sử dụng thông tin có trong phần [TÀI LIỆU CHÍNH THỨC] dưới đây để trả lời. Tuyệt đối không suy đoán hay thêm thắt thông tin không có trong tài liệu.
2. Trả lời bằng tiếng Việt lịch sự, thân thiện, rõ ràng, gạch đầu dòng các bước thao tác (nếu có).
3. Đính kèm liên kết trích dẫn nguồn ở cuối câu trả lời nếu có.
4. Nếu tài liệu không đủ thông tin, thông báo rõ ràng và đề xuất chuyển chuyên viên hỗ trợ.

[TÀI LIỆU CHÍNH THỨC]:
{context}

Câu hỏi của khách hàng: {query}
"""

def extract_direct_answer_fallback(query: str, context: str, citations: list[dict]) -> str:
    """
    Trích xuất câu trả lời chuẩn xác trực tiếp từ chunk tài liệu chính thức
    khi LLM API chưa cấu hình key thật.
    """
    if not context or not citations:
        return (
            "Dạ hiện tại hệ thống chưa tìm thấy tài liệu chính thức từ VinFast xác nhận thông tin này. "
            "Để đảm bảo tính chính xác, câu hỏi này đã được ghi nhận và chuyển cho chuyên viên kỹ thuật (Staff Review) "
            "để kiểm tra và phản hồi Quý khách sớm nhất ạ."
        )

    top_citation = citations[0]
    title = top_citation.get("title", "Tài liệu VinFast")
    url = top_citation.get("url", "https://vinfastauto.com/vn_vi")
    section = top_citation.get("section", "Chi tiết")

    # Lấy nội dung văn bản sạch
    clean_lines = []
    for line in context.split("\n"):
        line = line.strip()
        if line and not line.startswith("[Tài liệu"):
            clean_lines.append(line)

    summary_text = "\n".join(clean_lines[:6])

    response = (
        f"Dạ theo thông tin chính thức từ **{title}** (Mục: *{section}*):\n\n"
        f"{summary_text}\n\n"
        f"📎 **Nguồn tài liệu chính thức:** [{title}]({url})"
    )
    return response

async def process_chat_message(
    user_message: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Hàm xử lý hội thoại chính của Chatbot Agent (Core AI Slice):
    1. Kiểm tra an toàn khẩn cấp (Hard Safety Guardrails).
    2. Ẩn danh hóa PII nếu có.
    3. Tra cứu Knowledge Base qua RAG.
    4. Sinh câu trả lời kèm Citation URL.
    5. Đánh giá cờ duyệt Human-in-the-loop (Staff Review).
    """
    # Bước 1: Ẩn danh PII (nếu có SĐT thật / biển số thật)
    sanitized_text, is_pii, pii_types = sanitize_pii(user_message)

    # Bước 2: Kiểm tra Hard Safety Rules (Cháy, mất phanh, ngập nước...)
    is_critical, trigger_rule, priority = evaluate_hard_safety(user_message)
    if is_critical:
        reply_emergency = (
            f"🚨 **CẢNH BÁO AN TOÀN KHẨN CẤP ({trigger_rule})** 🚨\n\n"
            f"{EMERGENCY_SAFE_GUIDANCE}\n\n"
            f"📞 **Tổng đài cứu hộ khẩn cấp:** **{VINFAST_HOTLINE}** (Hoạt động 24/7)"
        )
        return {
            "reply": reply_emergency,
            "intent": "safety_adversarial_oos",
            "priority": "critical",
            "needs_staff_review": True,
            "is_safety_trigger": True,
            "citations": [
                {
                    "source_id": "SRC-003",
                    "title": "Thông tin cứu hộ và cứu hộ pin 24/7",
                    "url": "https://vinfastauto.com/vn_vi/thong-tin-cuu-ho-oto",
                    "section": "Cứu hộ khẩn cấp 24/7"
                }
            ]
        }

    # Bước 2.5: Kiểm tra câu hỏi ngoài phạm vi / thương hiệu khác / can thiệp trái phép
    text_lower = user_message.lower()
    oos_keywords = [
        "vé máy bay", "vietnam airlines", "vietjet", "tesla", "hyundai", "toyota", "honda",
        "thời tiết", "mặt trời", "áp mái", "hòa lưới", "tự đấu dây", "can thiệp tăng công suất",
        "giảm giá bí mật", "bẻ khóa", "hack động cơ", "phá khóa"
    ]
    if any(kw in text_lower for kw in oos_keywords):
        reply_no_source = (
            "Dạ em đã kiểm tra trong cơ sở dữ liệu hướng dẫn và chính sách chính thức của VinFast "
            "nhưng chưa có thông tin xác thực cho yêu cầu này. \n\n"
            "Để tránh cung cấp thông tin không chính xác, em đã tạo phiếu yêu cầu và chuyển tiếp "
            "cho bộ phận chuyên viên hỗ trợ (Staff Review). Quý khách sẽ nhận được phản hồi chính thức sớm nhất ạ."
        )
        return {
            "reply": reply_no_source,
            "intent": "safety_adversarial_oos",
            "priority": "low",
            "needs_staff_review": True,
            "is_safety_trigger": False,
            "citations": []
        }

    # Bước 3: Tra cứu tri thức từ ChromaDB Knowledge Base (Mục 2.4)
    rag_result = rag_service.retrieve(sanitized_text, top_k=2)

    # Nếu không có nguồn hoặc khoảng cách vượt ngưỡng -> Rule 2.4 NO_SOURCE
    if rag_result["status"] == "NO_SOURCE":
        reply_no_source = (
            "Dạ em đã kiểm tra trong cơ sở dữ liệu hướng dẫn và chính sách chính thức của VinFast "
            "nhưng chưa có thông tin xác thực cho yêu cầu này. \n\n"
            "Để tránh cung cấp thông tin không chính xác, em đã tạo phiếu yêu cầu và chuyển tiếp "
            "cho bộ phận chuyên viên hỗ trợ (Staff Review). Quý khách sẽ nhận được phản hồi chính thức sớm nhất ạ."
        )
        return {
            "reply": reply_no_source,
            "intent": "safety_adversarial_oos",
            "priority": "low",
            "needs_staff_review": True,
            "is_safety_trigger": False,
            "citations": []
        }

    # Bước 4: Tạo câu trả lời có căn cứ (Grounded Response)
    citations = rag_result["citations"]
    context_text = rag_result["context_text"]

    # Thử gọi LLM nếu có cấu hình key hợp lệ, nếu không thì dùng trích xuất chuẩn mực
    try:
        from src.services.llm import get_llm
        from src.config import get_settings
        settings = get_settings()

        # Kiểm tra xem key có phải placeholder không
        if settings.google_api_key and "your" not in settings.google_api_key.lower():
            llm = get_llm()
            prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context_text, query=sanitized_text)
            ai_msg = await llm.ainvoke(prompt)
            final_reply = ai_msg.content
        else:
            final_reply = extract_direct_answer_fallback(sanitized_text, context_text, citations)
    except Exception:
        # Graceful fallback: trích xuất trực tiếp
        final_reply = extract_direct_answer_fallback(sanitized_text, context_text, citations)

    # Bước 5: Xác định Intent và cờ Staff Review
    text_lower = user_message.lower()
    if any(kw in text_lower for kw in ["sạc", "trụ sạc", "pin", "thuê pin", "hết pin"]):
        intent = "charging_battery"
    elif any(kw in text_lower for kw in ["bảo dưỡng", "sửa chữa", "lỗi", "kêu", "cứu hộ", "lốp"]):
        intent = "service_incident"
    elif any(kw in text_lower for kw in ["bức xúc", "khiếu nại", "thái độ", "trừ tiền"]):
        intent = "complaint_feedback"
    else:
        intent = "sales_general_info"

    needs_review = is_hitl_mandatory(
        intent=intent,
        priority=priority,
        confidence_score=0.95,
        is_critical=False,
        rag_score=1.0 - (rag_result["best_distance"] / 2.0)
    )

    return {
        "reply": final_reply,
        "intent": intent,
        "priority": priority.lower(),
        "needs_staff_review": needs_review,
        "is_safety_trigger": False,
        "citations": citations
    }
