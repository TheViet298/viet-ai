"""Vehicle model recognition service using multimodal LLM (gpt-6-luna)."""

import asyncio
import base64
import json
import logging
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.config import get_settings
from src.services.image_routing import get_async_openai_client
from src.services.vision.contract import Candidate, VehicleResult, vehicle_result

LOGGER = logging.getLogger(__name__)

VINFAST_CANONICAL_MODELS = [
    "VF 3", "VF 5", "VF 6", "VF 7", "VF 8", "VF 9",
    "VF e34", "Lux A2.0", "Lux SA2.0", "Fadil",
]


class VehicleObservation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    is_vinfast: bool = False
    vehicle_model: str = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    candidates: list[dict] = Field(default_factory=list)


def normalize_vinfast_model(raw_name: str) -> str | None:
    if not raw_name:
        return None
    cleaned = raw_name.strip()
    upper = cleaned.upper().replace(" ", "").replace("-", "")
    for canon in VINFAST_CANONICAL_MODELS:
        canon_upper = canon.upper().replace(" ", "").replace("-", "")
        if canon_upper in upper or upper in canon_upper:
            return canon
    return None


async def recognize_vehicle_model(data: bytes, mime_type: str) -> dict:
    settings = get_settings()
    version = settings.vision_model
    threshold = 0.7

    def unavailable(reason: str) -> dict:
        return VehicleResult(
            status="unavailable",
            reason=reason,
            model_version=version,
            threshold=threshold,
        ).model_dump(mode="json")

    if not settings.agent_llm_enabled:
        return unavailable("llm_disabled")
    if not settings.openai_api_key and not settings.google_api_key:
        return unavailable("credentials_missing")

    prompt = (
        "Analyze this exterior vehicle image to identify the VinFast vehicle model. "
        "Recognizable models include: VF 3, VF 5, VF 6, VF 7, VF 8, VF 9, VF e34, Lux A2.0, Lux SA2.0, Fadil. "
        "Return a JSON object with: "
        "- is_vinfast (boolean): true if this is definitely a VinFast car, false otherwise. "
        "- vehicle_model (string): canonical model name (e.g. 'VF 3', 'VF 7') or 'unknown'. "
        "- confidence (float in [0, 1]): your certainty about the model identification. "
        "- candidates (list of objects with 'label' and 'confidence'). "
        "Never transcribe license plates, people, or personal information."
    )

    try:
        async with asyncio.timeout(settings.image_routing_timeout_s):
            client = get_async_openai_client()
            b64 = base64.b64encode(data).decode("ascii")
            res = await client.chat.completions.create(
                model=settings.vision_model,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                        ],
                    }
                ],
                max_tokens=512,
                temperature=0,
            )
            choice = res.choices[0]
            if choice.finish_reason not in ("stop", None):
                return unavailable("incomplete_response")
            content = choice.message.content or "{}"
            parsed = VehicleObservation.model_validate_json(content)

            canon_label = normalize_vinfast_model(parsed.vehicle_model) if parsed.is_vinfast else None
            score = parsed.confidence if canon_label else 0.0

            if canon_label and score >= threshold:
                candidates = [Candidate(label=canon_label, confidence=score)]
                if parsed.candidates:
                    for c in parsed.candidates:
                        c_label = normalize_vinfast_model(str(c.get("label", "")))
                        if c_label and c_label != canon_label:
                            c_conf = float(c.get("confidence", 0.1))
                            candidates.append(Candidate(label=c_label, confidence=min(score - 0.01, c_conf)))
                return VehicleResult(
                    status="candidate",
                    model_label=canon_label,
                    candidates=candidates,
                    model_version=version,
                    threshold=threshold,
                    requires_user_confirmation=True,
                ).model_dump(mode="json")
            else:
                fallback_candidates = [Candidate(label="unknown", confidence=max(0.0, score))]
                return VehicleResult(
                    status="unknown",
                    model_label=None,
                    candidates=fallback_candidates,
                    model_version=version,
                    threshold=threshold,
                    reason="below_provisional_threshold" if canon_label else "not_vinfast",
                    requires_user_confirmation=True,
                ).model_dump(mode="json")
    except (TimeoutError, asyncio.TimeoutError):
        return unavailable("inference_timeout")
    except Exception as exc:
        LOGGER.exception("Vehicle model recognition failed")
        return unavailable("inference_failed")
