"""Bounded evidence from a trusted server-side detector, never confirmed model facts."""

import re
from typing import Literal

from pydantic import Field, model_validator

from src.agents.guardrails import check_missing_fields
from src.services.vision.contract import DamageDetection, DamageResult, VisionEvidence

LABELS = {
    "dent": "móp",
    "scratch": "xước",
    "crack": "nứt",
    "glass shatter": "vỡ kính",
    "lamp broken": "vỡ đèn",
    "tire flat": "lốp xẹp",
}
CONFIRM = "Xác nhận hư hại trong ảnh"
REJECT = "Không xác nhận kết quả ảnh"


class CarddEvidence(DamageResult):
    source: Literal["cardd"] = "cardd"
    image_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9:_-]{1,128}$")
    turn: int = Field(ge=1)
    detections: list[DamageDetection] = Field(default_factory=list, max_length=100)
    confirmation: Literal["unconfirmed", "confirmed", "rejected"] = "unconfirmed"
    confirmation_turn: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def opaque_metadata(self):
        if self.model_version is not None and not re.fullmatch(r"[0-9a-f]{64}", self.model_version):
            raise ValueError("Expected checkpoint SHA256")
        if self.status in ("detected", "not_detected") and not self.image_id:
            raise ValueError("Executed evidence needs an image ID")
        # Reasons are codes, not arbitrary text from model/client output.
        if self.reason and not re.fullmatch(r"[a-z_]{1,64}", self.reason):
            raise ValueError("Expected a bounded reason code")
        return self


def make_cardd_signal(payload: dict, turn: int) -> dict:
    try:
        result = VisionEvidence.model_validate(payload)
        record = CarddEvidence(**result.damage.model_dump(), image_id=result.image_id, turn=turn)
    except (ValueError, TypeError):
        record = CarddEvidence(turn=turn, status="unavailable", reason="invalid_evidence")
    return {"turn": turn, "evidence": record.model_dump(mode="json")}


def consume_cardd_signal(state: dict, turn: int, text: str) -> dict:
    record = None
    try:
        if state.get("cardd_evidence"):
            prior = CarddEvidence.model_validate(state["cardd_evidence"])
            if 0 <= turn - prior.turn <= 2:
                record = prior
    except (ValueError, TypeError):
        pass
    fresh, changed = False, False
    pending = state.get("pending_cardd_signal")
    if isinstance(pending, dict) and pending.get("turn") == turn:
        try:
            incoming = CarddEvidence.model_validate(pending["evidence"])
            if incoming.turn != turn:
                raise ValueError("Signal turn mismatch")
            keys = ("image_id", "model_version", "status", "threshold", "detections")
            repeated = (
                record is not None
                and incoming.image_id is not None
                and all(getattr(record, k) == getattr(incoming, k) for k in keys)
            )
            if incoming.status == "not_requested":
                record = None
            elif not repeated:
                # Confirmation is a user event; it cannot be asserted by image metadata.
                record = incoming.model_copy(update={"confirmation": "unconfirmed", "confirmation_turn": None})
                fresh = record.status != "not_requested"
        except (KeyError, ValueError, TypeError):
            pass
    selection = text.strip().rstrip(".!").casefold()
    if not fresh and record and record.confirmation == "unconfirmed":
        if selection in (CONFIRM.casefold(), REJECT.casefold()):
            record.confirmation = "confirmed" if selection == CONFIRM.casefold() else "rejected"
            record.confirmation_turn = turn
            changed = True
    return {
        "pending_cardd_signal": None,
        "cardd_evidence": record.model_dump(mode="json") if record else None,
        "cardd_new_input": fresh,
        "cardd_confirmation_changed": changed,
    }


def evidence_for_turn(state: dict) -> dict | None:
    value = state.get("cardd_evidence")
    try:
        record = CarddEvidence.model_validate(value)
        if 0 <= state.get("turn", 0) - record.turn <= 2:
            return record.model_dump(mode="json")
    except (ValueError, TypeError):
        pass
    return None


def evidence_summary(record: dict) -> str:
    status = record["status"]
    if status == "detected":
        scores = record["detections"]
        names = sorted({LABELS[item["label"]] for item in scores})
        tentative = all(item["confidence"] < 0.5 for item in scores)
        prefix = "AI chỉ thấy dấu hiệu chưa chắc chắn: " if tentative else "AI đề xuất dấu hiệu: "
        text = prefix + ", ".join(names) + ". Đây chưa phải kết luận hư hại."
    elif status == "not_detected":
        text = "AI chưa phát hiện vùng hư hại đạt ngưỡng; kết quả này không xác nhận xe nguyên vẹn."
    elif status == "unavailable":
        text = "Chưa phân tích được ảnh ngoại thất; không có kết luận hư hại từ ảnh."
    else:
        return ""
    if record["confirmation"] == "confirmed":
        text = "Khách xác nhận ảnh có hư hại; các nhãn vẫn là dự đoán AI. " + text
    elif record["confirmation"] == "rejected":
        text = "Khách không xác nhận kết quả ảnh. " + text
    return text


def missing_fields_for_state(state: dict) -> list[str]:
    missing = check_missing_fields(state.get("intent"), state.get("captured_fields", {}))
    record = evidence_for_turn(state)
    if state.get("intent") == "Service/Incident" and record and record["confirmation"] == "confirmed":
        missing = [field for field in missing if field != "warning_symbol"]
    return missing


def confirmed_cardd_context(state: dict) -> str:
    record = evidence_for_turn(state)
    if not record or record["confirmation"] != "confirmed":
        return ""
    return (
        "Bằng chứng ảnh ngoại thất đã được khách xác nhận có hư hại; "
        "từng nhãn/bbox chỉ là giả thuyết AI, không phải nguồn tài liệu hướng dẫn sửa chữa. "
        f"image_id={record['image_id']}. " + evidence_summary(record)
    )
