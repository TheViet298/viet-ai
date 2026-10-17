from __future__ import annotations

import asyncio

from src.services.location_service import suggest_service_points
from src.services.rag_service import rag_service


async def vinfast_manual_search(query: str, vehicle_model: str | None = None) -> dict:
    """Search up to three verified passages within the configured UTF-8 byte budget."""
    if not query.strip():
        return {
            "status": "INVALID_INPUT",
            "message": "Provide a nonempty VinFast question, e.g. 'Bảo hành VF8 bao lâu?'",
            "citations": [],
        }
    return await asyncio.to_thread(rag_service.retrieve, query, top_k=3, vehicle_model=vehicle_model)


async def vinfast_station_search(case_id: str, customer_id: str) -> list[dict]:
    """Return at most five snapshot points through the shared engine after consent and ownership checks."""
    return suggest_service_points(case_id, customer_id)


async def vinfast_nearby_search(latitude: float, longitude: float, category: str,
                               vehicle_type: str = "CAR", radius_km: float = 50) -> dict:
    """Search service points through service_point_service after caller obtains consent or a manual reference centre.

    This deterministic tool is used by the customer action flow; coordinates never
    need to enter a language-model prompt or a case merely to perform a lookup.
    """
    if category not in {"ALL", "CHARGING_STATION", "SHOWROOM", "SERVICE_WORKSHOP", "OTHER"}:
        raise ValueError("Unsupported nearby category")
    if not 0 < radius_km <= 1000:
        raise ValueError("Invalid search radius")
    from src.services.service_point_service import search_service_points_catalog
    return await asyncio.to_thread(search_service_points_catalog, latitude, longitude, category, radius_km, 5, vehicle_type)
