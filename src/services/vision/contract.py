"""Versioned AI evidence, never a confirmed vehicle or a diagnosis."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DamageLabel = Literal["dent", "scratch", "crack", "glass shatter", "lamp broken", "tire flat"]


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Candidate(EvidenceModel):
    label: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class VehicleResult(EvidenceModel):
    status: Literal["candidate", "unknown", "unavailable", "not_requested"] = "not_requested"
    model_label: str | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    model_version: str | None = None
    threshold: float = Field(default=0.7, ge=0, le=1)
    reason: str | None = None
    requires_user_confirmation: Literal[True] = True

    @model_validator(mode="after")
    def consistent_status(self):
        if self.status == "candidate":
            if not self.candidates or self.model_label != self.candidates[0].label:
                raise ValueError("Candidate label must match top candidate")
            if self.candidates[0].confidence < self.threshold or not self.model_version:
                raise ValueError("Accepted candidate needs threshold and model version")
        elif self.model_label is not None:
            raise ValueError("Only candidate status may contain a proposed model label")
        if self.status == "unknown" and (not self.candidates or not self.model_version):
            raise ValueError("Unknown prediction needs evidence and model version")
        if self.status == "unavailable" and not self.reason:
            raise ValueError("Unavailable requires reason")
        if self.status in ("unavailable", "not_requested") and self.candidates:
            raise ValueError("Unexecuted tasks cannot contain predictions")
        return self


class DamageDetection(EvidenceModel):
    label: DamageLabel
    confidence: float = Field(ge=0, le=1)
    bbox_xyxy: tuple[float, float, float, float]

    @model_validator(mode="after")
    def valid_box(self):
        x1, y1, x2, y2 = self.bbox_xyxy
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError("Expected nonempty normalized xyxy box within image")
        return self


class DamageResult(EvidenceModel):
    status: Literal["detected", "not_detected", "unavailable", "not_requested"] = "not_requested"
    detections: list[DamageDetection] = Field(default_factory=list)
    model_version: str | None = None
    threshold: float = Field(default=0.25, ge=0, le=1)
    reason: str | None = None
    bbox_format: Literal["xyxy_normalized"] = "xyxy_normalized"

    @model_validator(mode="after")
    def consistent_status(self):
        if (self.status == "detected") != bool(self.detections):
            raise ValueError("Only detected status may contain detections")
        if self.status in ("detected", "not_detected") and not self.model_version:
            raise ValueError("Executed task needs model version")
        if any(d.confidence < self.threshold for d in self.detections):
            raise ValueError("Detection below reported threshold")
        if self.status == "unavailable" and not self.reason:
            raise ValueError("Unavailable requires reason")
        return self


class VisionEvidence(EvidenceModel):
    schema_version: Literal["1.0"] = "1.0"
    image_id: str = Field(min_length=1)
    vehicle: VehicleResult = Field(default_factory=VehicleResult)
    damage: DamageResult = Field(default_factory=DamageResult)
    ocr: Literal["deferred_to_ocr"] = "deferred_to_ocr"


def vehicle_result(scores: list[tuple[str, float]], version: str, threshold: float = 0.7) -> VehicleResult:
    candidates = sorted([Candidate(label=k, confidence=v) for k, v in scores], key=lambda c: -c.confidence)
    if not candidates:
        raise ValueError("Classifier returned no scores; report unavailable instead")
    accepted = candidates[0].confidence >= threshold
    return VehicleResult(
        status="candidate" if accepted else "unknown",
        model_label=candidates[0].label if accepted else None,
        candidates=candidates[:5],
        model_version=version,
        threshold=threshold,
        reason=None if accepted else "below_provisional_threshold",
    )


def damage_result(detections: list[dict], version: str, threshold: float = 0.25) -> DamageResult:
    validated = [DamageDetection.model_validate(d) for d in detections]
    selected = [d for d in validated if d.confidence >= threshold]
    return DamageResult(
        status="detected" if selected else "not_detected",
        detections=selected,
        model_version=version,
        threshold=threshold,
    )
