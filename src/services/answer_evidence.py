"""Select complete answer sections and reject descriptions posing as procedures."""
import re


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
