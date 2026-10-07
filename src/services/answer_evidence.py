"""Select complete answer sections and reject descriptions posing as procedures."""
import re
import unicodedata


def normalized(text: str) -> str:
    return " ".join("".join(c for c in unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
                            if not unicodedata.combining(c)).split())


def is_turtle_question(query: str) -> bool:
    return any(term in normalized(query) for term in ("con rua", "rua vang", "turtle"))


def clean_section(text: str) -> str:
    lines = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if line and line not in seen:
            lines.append(line)
            seen.add(line)
    return "\n".join(lines)


def answer_section(query: str, text: str) -> str:
    lower = query.casefold()
    subject = normalized(query)
    body = normalized(text)
    if any(term in subject for term in ("lai thu", "chay thu")) and not any(term in body for term in ("lai thu", "chay thu")):
        return ""
    if any(term in subject for term in ("gia lan banh", "chi phi lan banh")):
        if not any(term in body for term in ("lan banh", "du toan")):
            return ""
    elif any(term in subject for term in ("gia xe", "bang gia")):
        if not any(term in body for term in ("gia", "chi phi")):
            return ""
    if any(term in subject for term in ("cac dong xe", "cac mau xe", "mau xe", "dai san pham")) and not any(term in body for term in ("vf3", "vf 3", "vf5", "vf 5", "vf6", "vf 6", "vf7", "vf 7", "vf8", "vf 8", "vf9", "vf 9")):
        return ""
    if is_turtle_question(query):
        subjects = ("rua", "turtle", "gioi han cong suat", "han che cong suat", "limited driving power")
        lines = text.splitlines()
        start = next((i for i, line in enumerate(lines) if any(term in normalized(line) for term in subjects)), None)
        if start is None:
            return ""
        end = next((i for i in range(start + 1, len(lines))
                    if normalized(lines[i]).startswith(("chi bao ", "den bao "))
                    and not any(term in normalized(lines[i]) for term in subjects)), len(lines))
        section = "\n".join(lines[start:end]).strip()
        # An indicator list is not an explanation of its meaning.
        if not any(term in normalized(section) for term in ("khi ", "la ", "giam", "han che")):
            return ""
        return section
    if "bảo hành" in lower and "điều kiện" in lower and not any(term in lower for term in ("bao lâu", "thời hạn")):
        # A duration's 'whichever comes first' clause does not explain eligibility.
        body = text.casefold()
        if "sử dụng tiêu chuẩn" in lower and not re.search(r"(?:sử dụng tiêu chuẩn|điều kiện tiêu chuẩn)[^\n]{0,80}(?:được hiểu|là\s|bao gồm|không dùng|không sử dụng)", body):
            return ""
        components = ("pin", "sơn", "kim loại", "xuyên thủng", "gỉ", "phụ tùng", "phụ kiện", "truyền động", "ắc-quy", "ắc quy", "bộ phận treo", "lốp")
        if not any(term in lower for term in components) and any(term in body for term in components):
            return ""
        if not any(term in body for term in ("sử dụng đúng", "bảo dưỡng định kỳ", "tuân thủ", "không bảo hành", "không áp dụng", "dịch vụ thương mại", "được hiểu là", "bao gồm", "không sử dụng để", "không dùng để")):
            return ""
    if "đặt lịch" in lower:
        lines = clean_section(text).splitlines()
        start = next((i for i, line in enumerate(lines) if "đặt lịch" in line.casefold()), None)
        if start is None:
            return ""
        end = next((i for i in range(start + 1, len(lines)) if re.match(r"^\d+(?:\.\d+)*\.\s", lines[i]) or "kiểm tra cảnh báo" in lines[i].casefold()), len(lines))
        section = "\n".join(lines[start:end])
        if any(term in lower for term in ("hướng dẫn", "cách", "làm thế nào", "như thế nào")):
            if not re.search(r"bước\s*\d+|(?:bấm|chọn|nhập)\s", section, re.I):
                return ""
            steps = [int(n) for n in re.findall(r"bước\s*(\d+)", section, re.I)]
            if steps and steps != list(range(1, max(steps) + 1)):
                return ""
        return section
    if "bảo hành" in lower and any(term in lower for term in ("bao lâu", "thời hạn", "mấy năm")):
        components = ("pin", "sơn", "kim loại", "xuyên thủng", "gỉ", "phụ tùng", "phụ kiện", "truyền động", "ắc quy", "bộ phận treo", "lốp")
        requested = [term for term in components if term in lower]
        if not requested:
            lines = text.splitlines()
            boundary = next((i for i, line in enumerate(lines) if any(term in line.casefold() for term in components)), len(lines))
            text = "\n".join(lines[:boundary])
            # A whole-vehicle question cannot use a component policy or a menu.
            if any(term in text.casefold() for term in components):
                return ""
            if not re.search(r"\d+\s*năm", text, re.I):
                return ""
            if "the all new" in text.casefold() and "the all new" not in lower:
                return ""
    return text
