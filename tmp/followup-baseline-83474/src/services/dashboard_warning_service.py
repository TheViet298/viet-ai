"""Resolve reported dashboard warnings against the local reference dataset.

This is text lookup, not image recognition or a verified vehicle diagnosis.
"""

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path


def normalize(text: str) -> str:
    return " ".join("".join(
        c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
        if not unicodedata.combining(c)
    ).split())


def normalize_model(model: str) -> str:
    return normalize(model).replace("vinfast", "").replace("plus", "").replace(" ", "")


@lru_cache(maxsize=1)
def warning_records() -> list[dict]:
    path = Path(__file__).resolve().parents[2] / "dataset/img_warning_taplo/dashboard_warnings_full.json"
    return json.loads(path.read_text(encoding="utf-8"))


ALIASES = {
    "rapid_leak": ["ro ri ap suat lop nhanh", "giam ap suat dot ngot"],
    "low_pressure": ["ap suat lop thap", "lop non hoi"],
    "over_pressure": ["ap suat lop qua cao", "ap suat lop cao"],
    "high_temperature": ["nhiet do lop cao"],
    "sensor_fault": ["loi cam bien ap suat lop", "mat tin hieu cam bien lop"],
    "sensor_battery_low": ["pin cam bien lop yeu", "pin cam bien lop thap"],
    "tpms_system_error": ["loi he thong tpms", "loi he thong theo doi ap suat lop"],
    "brake_system_fault": ["canh bao he thong phanh", "loi he thong phanh", "den phanh do",
                           "loi he thong tro luc phanh", "mat tro luc phanh"],
    "turtle_mode_power_limited": ["rua vang", "turtle mode", "limp home", "hieu nang xe bi giam"],
    "high_voltage_battery_fault": ["loi pin cao ap", "loi he thong pin cao ap"],
    "eps_steering_fault": ["loi tro luc lai", "canh bao eps"],
    "airbag_warning": ["canh bao tui khi", "loi tui khi"],
    "abs_fault": ["loi abs", "canh bao abs"],
    "esc_fault": ["loi esc", "canh bao esc"],
    "door_ajar_warning": ["canh bao mo cua", "cua chua dong"],
    "seatbelt_warning": ["canh bao day an toan", "nhac nho day an toan"],
    "ready_mode_indicator": ["den ready", "chi bao ready"],
}


VISIBLE_WARNING_LABELS = {
    "turtle": "Biểu tượng rùa — cảnh báo hạn chế công suất",
    "abs": "Đèn ABS",
    "brake": "Đèn cảnh báo hệ thống phanh",
    "esc": "Biểu tượng xe trượt — cảnh báo cân bằng điện tử/chống trượt",
    "general_warning": "Tam giác chấm than — cảnh báo chung",
    "tpms": "Đèn cảnh báo áp suất lốp (TPMS)",
    "battery": "Đèn cảnh báo pin/ắc quy",
    "eps": "Đèn cảnh báo trợ lực lái",
    "airbag": "Đèn cảnh báo túi khí",
    "seatbelt": "Đèn nhắc thắt dây an toàn",
    "parking_brake": "Đèn phanh đỗ",
}


def describe_dashboard_image(signals: list[dict]) -> str:
    """Describe validated visual evidence without declaring mechanical failures."""
    lines = []
    colors = {"yellow": "vàng", "red": "đỏ", "green": "xanh lá", "unknown": "chưa rõ màu"}
    for signal in signals:
        if signal.get("confidence", 0) < .8 or signal.get("needs_clarification") or signal.get("analysis_error"):
            continue
        if signal.get("ocr_text"):
            quoted = signal["ocr_text"].replace("\n", " — ")
            lines.append(f'- **Chữ cảnh báo đọc được:** “{quoted}”.')
        for icon in signal.get("visible_warnings", []):
            label = VISIBLE_WARNING_LABELS.get(icon.get("kind"))
            if label and icon.get("confidence", 0) >= .8:
                line = f'- **{label}** ({colors.get(icon.get("color"), "chưa rõ màu")}).'
                if line not in lines:
                    lines.append(line)
    if not lines:
        return ""
    return "Em nhận diện được các cảnh báo trong ảnh:\n\n" + "\n".join(lines)


def merge_dashboard_clarification(previous: str, current: str) -> str:
    """An explicit answer replaces a disputed model or symptom for lookup."""
    previous = normalize(previous)
    current = normalize(current)
    model_pattern = r"\bvf\s*(e34|[356789])(?:\s*plus)?\b"
    if re.search(model_pattern, current):
        previous = re.sub(model_pattern, "", previous)
    if any(alias in current for aliases in ALIASES.values() for alias in aliases):
        for aliases in ALIASES.values():
            for alias in aliases:
                previous = previous.replace(alias, "")
    return previous + "\n" + current


def lookup_dashboard_warning(text: str, model: str | None) -> tuple[bool, str, list[dict], str]:
    normalized = normalize(text)
    explicit_models = {
        normalize_model(match.group(0))
        for match in re.finditer(r"\bvf\s*(e34|[356789])\b", normalized)
    }
    model_code = (next(iter(explicit_models)) if len(explicit_models) == 1
                  else "" if explicit_models else normalize_model(model or ""))
    keys = {
        key for key, aliases in ALIASES.items()
        if any(alias in normalized for alias in aliases)
    }
    is_dashboard = bool(keys) or any(word in normalized for word in (
        "tap-lo", "tap lo", "tpms", "den canh bao", "dashboard",
    ))
    # Only an unambiguous warning on a known model yields guidance.
    records = [item for item in warning_records()
               if normalize_model(item["vehicle_model"]) == model_code
               and item["symptom_key"] in keys] if is_dashboard else []
    if len(keys) != 1 or len(records) != 1:
        records = []
    # An unresolved citation must not suppress a reported urgent symptom.
    risk = "CRITICAL" if "brake_system_fault" in keys else (
        "HIGH" if keys & {"rapid_leak", "turtle_mode_power_limited",
                          "high_voltage_battery_fault", "eps_steering_fault"} else "MEDIUM"
    )
    return is_dashboard, model_code.upper() or "UNKNOWN", records, risk
