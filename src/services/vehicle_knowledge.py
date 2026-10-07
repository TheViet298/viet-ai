"""General vehicle concepts, separate from model-specific facts and diagnosis."""
import re

from src.agents.context_manager import resolve_policy_conflict
from src.services.answer_evidence import normalized

KNOWLEDGE_NOTE = "Đây là kiến thức chung về xe, chưa đối chiếu sổ tay đúng mẫu/đời xe; không phải kết luận chẩn đoán."


def is_vehicle_comparison(text: str) -> bool:
    lower = normalized(text)
    return bool(re.search(r"\bvf\s*(?:e34|[356789])\b", lower) and
                re.search(r"\b(?:so sanh|khac nhau|nen mua|nen chon|vs|versus)\b", lower))


def is_general_vehicle_question(text: str) -> bool:
    if is_vehicle_comparison(text):
        return False
    lower = normalized(text)
    definition = any(term in lower for term in ("la gi", "y nghia", "nghia la gi", "giai thich", "dinh nghia"))
    generic_definition = (definition and not re.search(r"\bvf\s*(?:e34|[356789])\b|\d", lower)
                          and not any(term in lower for term in ("bao nhieu", "hien nay", "hien tai", "xe toi", "xe cua toi")))
    restricted = (
        "gia", "phi sac", "bao hanh", "chinh sach", "uu dai", "khuyen mai", "thong so",
        "bao nhieu", "bao lau", "dung luong", "dien ap", "kwh", "dat lich", "lai thu",
        "sua chua", "thao", "dau day", "chan doan", "hieu chinh", "do kiem",
        "bi mat", "noi bo", "thang sau", "khong cong khai", "khong khai",
        "thoi tiet", "may bay", "pin mat troi", "hoa luoi",
    )
    if generic_definition:
        restricted = tuple(term for term in restricted if term not in {"dung luong", "dien ap", "kwh"})
    if resolve_policy_conflict(text) or any(re.search(r"\b" + re.escape(term) + r"\b", lower) for term in restricted):
        return False
    question = any(term in lower for term in ("la gi", "la cai gi", "y nghia", "giai thich", "nguyen ly", "hoat dong", "tai sao", "khi nao", "khac nhau", "uu nhuoc", "phan biet", "tac dung", "dung de", "cong dung", "viet tat", "tim hieu"))
    question = question or bool(re.fullmatch(r"(?:abs|esp|esc|tpms|bms|soc|soh|acc|lka|ldw|adas)[?! .]*", lower))
    vehicle_topic = bool(re.search(r"\b(?:xe|pin|sac|phanh|lop|dong co|abs|esp|esc|tpms|bms|soc|soh|acc|lka|ldw|kwh|rua|turtle|adas)\b", lower))
    return question and vehicle_topic


def common_vehicle_explanation(text: str) -> str | None:
    lower = normalized(text)
    definitions = [
        (r"\bsoc\b", "SOC (State of Charge) là mức pin còn lại, thường được biểu thị bằng phần trăm so với dung lượng sử dụng được của pin. SOC cho biết trạng thái nạp hiện tại, không phải sức khỏe hay mức chai của pin."),
        (r"\bsoh\b", "SOH (State of Health) là chỉ số sức khỏe pin, phản ánh mức suy giảm so với trạng thái ban đầu. SOH khác SOC: SOC là mức pin đang còn, SOH liên quan đến khả năng của pin sau thời gian sử dụng. Cách đánh giá SOH phụ thuộc hệ thống quản lý pin."),
        (r"\b(?:ac|dc)\b.*sac|sac.*\b(?:ac|dc)\b", "Sạc AC dùng điện xoay chiều; bộ sạc trên xe chuyển thành điện một chiều để nạp pin. Sạc DC cung cấp điện một chiều từ trụ tới hệ thống pin, không qua bộ chuyển đổi AC trên xe. Tốc độ thực tế phụ thuộc xe, trụ sạc, mức pin và nhiệt độ; DC không phải lúc nào cũng đạt công suất tối đa ghi trên trụ."),
        (r"dung luong pin|\bkwh\b", "Dung lượng năng lượng của pin xe thường được biểu thị bằng kWh (kilowatt-giờ), là lượng năng lượng pin có thể lưu trữ. kWh khác kW: kWh đo năng lượng, kW đo công suất. Pin có dung lượng lớn hơn không tự động bảo đảm quãng đường dài hơn vì còn phụ thuộc mức tiêu thụ và điều kiện vận hành."),
        (r"mo[- ]?men xoan", "Mô-men xoắn là lực quay do động cơ tạo ra, thường biểu thị bằng N·m. Khi được truyền tới bánh xe qua hệ truyền động, nó góp phần tạo lực kéo. Khả năng tăng tốc còn phụ thuộc công suất, tỷ số truyền, khối lượng và độ bám đường."),
        (r"\bacc\b", "ACC là kiểm soát hành trình thích ứng: hệ thống hỗ trợ giữ tốc độ đặt và điều chỉnh tốc độ để duy trì khoảng cách với xe phía trước trong điều kiện hoạt động cho phép. Đây là hỗ trợ người lái, không phải tự lái; phạm vi hoạt động phụ thuộc xe."),
        (r"\b(?:lka|ldw)\b", "LDW cảnh báo khi xe có xu hướng lệch làn; LKA có thể hỗ trợ điều chỉnh hướng lái để giữ xe trong làn trong điều kiện cho phép. Hai chức năng khác nhau và đều phụ thuộc khả năng nhận diện vạch đường. Người lái vẫn cần quan sát và điều khiển xe."),
        (r"\b(?:rua|turtle)\b|gioi han cong suat", "Biểu tượng con rùa (Turtle Mode) thường báo xe đang giới hạn công suất, nên khả năng tăng tốc có thể giảm. Đây là cơ chế bảo vệ; pin yếu, nhiệt độ bất thường hoặc lỗi hệ thống có thể là những nguyên nhân, nhưng chỉ biểu tượng này chưa đủ để xác định nguyên nhân của xe cụ thể."),
        (r"\babs\b", "ABS là hệ thống chống bó cứng phanh. Khi phanh mạnh, hệ thống điều chỉnh lực phanh để hạn chế bánh xe bị khóa và giúp người lái duy trì khả năng điều hướng. ABS không bảo đảm quãng đường phanh luôn ngắn hơn trong mọi điều kiện."),
        (r"\b(?:esp|esc)\b", "ESP/ESC là hệ thống cân bằng điện tử. Hệ thống theo dõi chuyển động của xe và có thể điều chỉnh lực phanh từng bánh hoặc công suất động cơ để hỗ trợ giữ ổn định khi xe có xu hướng mất kiểm soát."),
        (r"\btpms\b", "TPMS là hệ thống theo dõi áp suất lốp. Hệ thống cảnh báo khi phát hiện áp suất bất thường; một số loại đo trực tiếp bằng cảm biến, một số loại suy ra từ tốc độ quay bánh xe. Mức áp suất đúng cần xem trên tem xe hoặc sổ tay của xe cụ thể."),
        (r"\bbms\b", "BMS là hệ thống quản lý pin. Hệ thống theo dõi trạng thái pin, điện áp và nhiệt độ, đồng thời phối hợp kiểm soát quá trình sạc/xả để bảo vệ pin. Tính năng và giới hạn cụ thể phụ thuộc thiết kế của từng xe."),
        (r"phanh tai sinh", "Phanh tái sinh dùng mô-tơ điện để làm xe chậm lại và chuyển một phần năng lượng chuyển động thành điện nạp về pin. Hiệu quả phụ thuộc trạng thái pin, nhiệt độ và điều kiện vận hành; hệ thống phanh ma sát vẫn cần thiết."),
        (r"\badas\b", "ADAS là nhóm hệ thống hỗ trợ người lái, có thể gồm cảnh báo va chạm, hỗ trợ giữ làn và kiểm soát hành trình thích ứng. Các tính năng cụ thể phụ thuộc xe; người lái vẫn cần quan sát và chịu trách nhiệm điều khiển."),
    ]
    answers = [answer for pattern, answer in definitions if re.search(pattern, lower)]
    return "\n\n".join(answers) if answers else None
