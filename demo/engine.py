"""Rule-based classification and extractive retrieval for the standalone demo."""
import json
import re
import unicodedata
from pathlib import Path
from uuid import uuid4

from store import normalize


def redact(text):
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email đã ẩn]", text)
    return re.sub(r"(?<!\d)(?:\+84|0)\d{9,10}(?!\d)", "[số điện thoại đã ẩn]", text)


class Engine:
    def __init__(self, store, rules_path):
        self.store = store
        self.rules = json.loads(Path(rules_path).read_text())

    @staticmethod
    def positive(text, keyword):
        text, keyword = unicodedata.normalize("NFC", text.lower()), unicodedata.normalize("NFC", keyword.lower())
        for match in re.finditer(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", text):
            prefix = text[max(0, match.start() - 25):match.start()]
            if not re.search(r"(?:không|chưa|hết)(?: bị| có| thấy| còn| xuất hiện)*\s*$", prefix):
                return True
        return False

    def urgent(self, text):
        for word in self.rules["urgent_keywords"]:
            if self.positive(text, word):
                return word
        composite = self.rules["urgent_composite"]
        if self.positive(text, composite["signal"]) and any(self.positive(text, word) for word in composite["contexts"]):
            return "rùa vàng + ngữ cảnh nguy hiểm"
        return None

    def respond(self, message, session_id=None):
        message = redact(message.strip())
        session_id = session_id or uuid4().hex
        context = self.store.context(session_id)
        previous = context.get("history", [])[-7:]
        full = " ".join(previous + [message])
        current = normalize(message)
        model = re.search(r"\bvf\s*([3-9])\b", full, re.I)
        if model:
            context["model"] = "VF" + model.group(1)
        seats = re.search(r"\b([2-9])\s*(?:cho|nguoi)\b", normalize(full))
        if seats:
            context["seats"] = int(seats.group(1))
        if any(word in current for word in ["do thi", "di pho", "thanh pho"]):
            context["usage"] = "Di chuyển đô thị"
        elif "gia dinh" in current:
            context["usage"] = "Gia đình"
        if any(word in current for word in ["dang chay", "dang di", "cao toc"]):
            context["operational_status"] = "Đang di chuyển"
        if any(word in current for word in ["da dung", "dang do", "dung xe", "dung han", "bai do", "o nha", "an toan"]):
            context["operational_status"] = "Đã dừng / đỗ"

        trigger = self.urgent(message)
        technical = trigger or any(self.positive(message, word) for word in self.rules["technical_keywords"])
        if technical:
            context["intent"] = "technical"
            context["problem"] = message
        elif not context.get("awaiting"):
            care = any(normalize(word) in current for word in self.rules["customer_care_keywords"])
            product = bool(re.search(r"\bvf\s*[3-9]\b", message, re.I)) or any(normalize(word) in current for word in self.rules["product_keywords"])
            context["intent"] = "product" if product and not care else "customer_care"
        intent = context.get("intent", "customer_care")
        result = {"session_id": session_id, "intent": intent, "priority": None, "citations": [], "missing_fields": [], "quick_replies": [], "case_id": None, "status": "ANSWER", "trace": ["Kiểm tra từ khóa URGENT", "Phân loại tin nhắn bằng luật"]}
        if trigger:
            result.update(priority="URGENT", status="HANDOFF", urgent_trigger=trigger)
            case_id = self.store.create_case(session_id, "URGENT", full, context)
            result["case_id"] = case_id
            result["message"] = f"Đang chuyển thông tin tới nhân viên kỹ thuật (con người) xử lý. Hồ sơ {case_id} đã vào hàng đợi kỹ thuật của demo với mức URGENT. Nếu có thể, hãy dừng ở vị trí an toàn và liên hệ hỗ trợ khẩn cấp phù hợp."
            result["trace"].append("Bỏ qua hỏi bổ sung → tạo hồ sơ URGENT")
            context["awaiting"] = False
            context["turns"] = 0
        elif intent == "technical":
            problem = context.get("problem", full)
            priority = "HIGH" if any(self.positive(problem, word) for word in self.rules["high_keywords"]) else ("LOW" if any(normalize(word) in normalize(problem) for word in self.rules["low_keywords"]) else "MEDIUM")
            missing = [field for field in ["model", "operational_status"] if not context.get(field)]
            result["priority"] = priority
            if missing and context.get("turns", 0) < self.rules["max_clarification_turns"]:
                context["turns"] = context.get("turns", 0) + 1
                context["awaiting"] = True
                result.update(status="CLARIFICATION", missing_fields=missing, message="Anh/chị cho biết dòng xe và xe đang di chuyển hay đã dừng ở vị trí an toàn nhé. Tôi cần thông tin này để chuẩn bị hồ sơ cho nhân viên kỹ thuật.", quick_replies=["VF8, đã dừng an toàn", "VF5, đang đỗ ở nhà", "Chưa biết dòng xe"])
                result["trace"].append(f"Thiếu ngữ cảnh → hỏi bổ sung lượt {context['turns']}/2")
            else:
                case_id = self.store.create_case(session_id, priority, full, context)
                result.update(status="HANDOFF", case_id=case_id, missing_fields=missing, message=f"Tôi đã ghi nhận vấn đề ở mức {priority}. Hồ sơ {case_id} đã được đưa vào hàng đợi kỹ thuật của demo để nhân viên xem xét. " + ("Một số ngữ cảnh còn thiếu được ghi trong hồ sơ." if missing else "Anh/chị có thể theo dõi trạng thái ở bảng bên phải."))
                context.update(awaiting=False, turns=0)
                result["trace"].append("Tạo hồ sơ kỹ thuật → chờ con người tiếp nhận")
        elif intent == "product" and not context.get("model") and not (context.get("usage") and context.get("seats")) and context.get("turns", 0) < 2:
            context.update(awaiting=True, turns=context.get("turns", 0) + 1)
            result.update(status="CLARIFICATION", missing_fields=["usage", "seats"], message="Để tư vấn phù hợp, anh/chị cần xe cho gia đình hay đi lại trong đô thị, và cần bao nhiêu chỗ? Nếu đã quan tâm một dòng xe, hãy cho tôi biết tên xe.", quick_replies=["Đi đô thị, 4 chỗ", "Gia đình, 5 chỗ", "Tôi muốn tìm hiểu VF9"])
            result["trace"].append("Kiểm tra ngữ cảnh tư vấn → hỏi nhu cầu sử dụng")
        else:
            records = self.store.retrieve(full, intent, context.get("model"), context.get("seats"))
            result["trace"].extend(["Tra cứu SQLite", "Xếp hạng theo ngữ cảnh và từ khóa", "Trả lời trích xuất kèm nguồn"])
            if records:
                result["message"] = "\n\n".join(record["text"] for record in records)
                result["citations"] = [{key: record.get(key) for key in ["title", "url", "score", "verified_at", "provenance"]} for record in records]
            else:
                result.update(status="NO_SOURCE", message="Database demo chưa có nguồn phù hợp cho câu hỏi này. Tôi chưa thể xác nhận thông tin; anh/chị có thể hỏi về ứng dụng, đặt lịch dịch vụ, tổng đài hoặc một dòng xe cụ thể.", quick_replies=["Cách đặt lịch bảo dưỡng", "Tìm hiểu VF8", "Liên hệ chăm sóc khách hàng"])
            context.update(awaiting=False, turns=0)
        context["history"] = previous + [message]
        result["context"] = {key: context[key] for key in ["model", "seats", "usage", "operational_status"] if key in context}
        self.store.save(session_id, context, message, result["message"])
        return result
