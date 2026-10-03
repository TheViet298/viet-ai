from __future__ import annotations

import asyncio

from src.services.location_service import suggest_service_points
from src.services.rag_service import rag_service


async def vinfast_manual_search(query: str, vehicle_model: str | None = None) -> dict:
    """Search up to three verified official manual chunks, capped at 1,200 tokens."""
    if not query.strip():
        return {
            "status": "INVALID_INPUT",
            "message": "Provide a nonempty VinFast question, e.g. 'Bảo hành VF8 bao lâu?'",
            "citations": [],
        }
    return await asyncio.to_thread(rag_service.retrieve, query, top_k=3, vehicle_model=vehicle_model)


async def vinfast_station_search(case_id: str, customer_id: str) -> list[dict]:
    """Return at most five named demo service points after consent and ownership checks."""
    return suggest_service_points(case_id, customer_id)
