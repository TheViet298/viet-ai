from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from src.agents.context_manager import resolve_policy_conflict, token_count
from src.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def source_registry() -> dict[str, dict]:
    """Use the project's reviewed registry, never invented HTTP verification."""
    registry = {}
    for line in (PROJECT_ROOT / "docs/data-sources.md").read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7 or not re.fullmatch(r"\*\*SRC-\d+\*\*", cells[0]) or "Đã xác minh (200 OK)" not in cells[4]:
            continue
        try:
            date.fromisoformat(cells[5])
        except ValueError:
            continue
        match = re.search(r"`(https://[^`]+)`", cells[2])
        if match:
            registry[cells[0].strip("*")] = {
                "title": cells[1],
                "url": match.group(1),
                "source_type": cells[3].strip("`"),
                "status_code": 200,
                "verified_at": cells[5],
            }
    return registry


def valid_citation(citation: dict, model: str | None = None) -> bool:
    source = source_registry().get(citation.get("source_id"))
    if not source or source["url"] != citation.get("url"):
        return False
    if urlparse(citation["url"]).hostname not in {"vinfastauto.com", "om.vinfastauto.com"}:
        return False
    if citation.get("status_code") != 200 or citation.get("verified_at") != source["verified_at"]:
        return False
    normalized = {re.sub(r"\s+", "", str(m)).upper() for m in citation.get("applicable_models", [])}
    if model and "ALL" not in normalized and model.upper() not in normalized:
        return False
    if not normalized or not citation.get("relevant_snippet"):
        return False
    try:
        if not 0 <= float(citation["distance"]) <= get_settings().rag_max_distance:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    return not resolve_policy_conflict(citation["relevant_snippet"])


class RAGService:
    def retrieve(self, query: str, top_k: int = 3, vehicle_model: str | None = None) -> dict:
        settings = get_settings()
        no_source = {"status": "NO_SOURCE", "best_distance": None, "citations": []}
        if not Path(settings.chroma_persist_dir, "chroma.sqlite3").is_file():
            return no_source
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir, settings=ChromaSettings(anonymized_telemetry=False)
            )
            collection = client.get_collection("vinfast_knowledge_base")
            count = collection.count()
            if not count:
                return no_source
            result = collection.query(
                query_texts=[query],
                n_results=min(max(1, top_k), 3, count),
                include=["documents", "metadatas", "distances"],
            )
            return self.filter_results(result, vehicle_model)
        except Exception:
            return no_source

    def filter_results(self, result: dict, vehicle_model: str | None = None) -> dict:
        registry = source_registry()
        citations = []
        budget = 1200
        for doc, meta, distance, chunk_id in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0], result["ids"][0], strict=True
        ):
            meta = meta or {}
            source = registry.get(meta.get("source_id"))
            if not source or source["url"] != meta.get("url"):
                continue
            models = meta.get("applicable_models", "")
            models = models.split(",") if isinstance(models, str) else models
            snippet = (doc or "").encode("utf-8")[:budget].decode("utf-8", errors="ignore")
            citation = {
                **source,
                "source_id": meta["source_id"],
                "chunk_id": chunk_id,
                "applicable_models": models,
                "relevant_snippet": snippet,
                "distance": distance,
            }
            if not valid_citation(citation, vehicle_model):
                continue
            citations.append(citation)
            budget -= token_count(snippet)
            if len(citations) >= 3 or budget <= 0:
                break
        return {
            "status": "SUCCESS" if citations else "NO_SOURCE",
            "citations": citations,
            "best_distance": min(c["distance"] for c in citations) if citations else None,
        }


rag_service = RAGService()
