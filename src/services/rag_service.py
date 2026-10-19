from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from datetime import date
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse

from src.agents.context_manager import resolve_policy_conflict, utf8_size
from src.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_cache_lock = RLock()


def words(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"vf\s*(e34|[356789])", r"vf\1", normalized)
    return set(re.findall(r"\w+", normalized)) - {"xe", "vinfast", "là", "của", "có", "bao", "nhiêu", "những", "nào", "được", "ô", "tô", "điện", "cho", "và", "thì", "để", "cách"}


def select_supported_evidence(query: str, citations: list[dict]) -> list[dict]:
    """Preserve complete source lines and their conditions; never invent facts."""
    from src.services.answer_evidence import answer_section, has_color_evidence, is_color_question
    selected = []
    seen = set()
    for citation in citations:
        if is_color_question(query) and not has_color_evidence(citation):
            continue
        lines = citation["relevant_snippet"].splitlines()
        if not lines:
            continue
        # Chunks are bounded complete sections. Never trim required list steps.
        excerpt = answer_section(query, "\n".join(lines))
        if not excerpt or excerpt in seen:
            continue
        seen.add(excerpt)
        selected.append({**citation, "relevant_snippet": excerpt})
    return selected


@lru_cache(maxsize=4)
def _collection(path: str):
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    # Register the optional function before Chroma deserializes its saved config.
    from src.services import multilingual_embeddings  # noqa: F401
    client = chromadb.PersistentClient(path=path, settings=ChromaSettings(anonymized_telemetry=False))
    return client.get_collection("vinfast_knowledge_base")


def get_collection(path: str):
    with _cache_lock:
        return _collection(path)


@lru_cache(maxsize=4)
def _corpus(path: str, count: int, revision: tuple):
    return get_collection(path).get(include=["documents", "metadatas", "embeddings"])


def get_corpus(path: str, count: int):
    # A same-count upsert changes SQLite/WAL state and invalidates this snapshot.
    revision = tuple((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in (Path(path) / "chroma.sqlite3", Path(path) / "chroma.sqlite3-wal") if p.is_file())
    with _cache_lock:
        return _corpus(path, count, revision)


def knowledge_fingerprint(path: str) -> str:
    """Hash logical content and vectors; SQLite housekeeping is excluded."""
    import numpy as np
    collection = get_collection(path)
    corpus = get_corpus(path, collection.count())
    digest = sha256()
    for i in sorted(range(len(corpus['ids'])), key=lambda j: corpus['ids'][j]):
        digest.update(json.dumps([corpus['ids'][i], corpus['documents'][i], corpus['metadatas'][i]], ensure_ascii=False, sort_keys=True).encode('utf-8'))
        digest.update(np.asarray(corpus['embeddings'][i], dtype='<f4').tobytes())
    return digest.hexdigest()


def model_applies(meta: dict, model: str | None) -> bool:
    if not model:
        return True
    models = meta.get("applicable_models", "")
    models = models.split(",") if isinstance(models, str) else models
    normalized = {re.sub(r"\s+", "", str(m)).upper() for m in models}
    return "ALL" in normalized or re.sub(r"\s+", "", model).upper() in normalized


def rank_candidates(query: str, rows: list[tuple]) -> list[tuple]:
    terms = words(query)
    purpose = requested_source_type(query)
    registry = source_registry()
    document_words = [words(row[0] or "") for row in rows]
    frequencies = Counter(term for terms_in_doc in document_words for term in terms_in_doc)
    total = max(1, len(rows))
    def score(pair):
        row, terms_in_doc = pair
        overlap = sum(math.log(1 + total / frequencies[t]) for t in terms & terms_in_doc)
        total_weight = sum(math.log(1 + total / max(1, frequencies[t])) for t in terms) or 1
        lexical = overlap / total_weight
        semantic = max(0, 1 - float(row[2]) / 2)
        source_type = (row[1] or {}).get('source_type') or registry.get((row[1] or {}).get('source_id'), {}).get('source_type')
        purpose_match = 0.2 if purpose and source_type == purpose else 0
        return (0.35 * lexical + 0.65 * semantic + purpose_match, -float(row[2]))
    return [row for row, _ in sorted(zip(rows, document_words, strict=True), key=score, reverse=True)]


def requested_source_type(query: str, *, source_need: str | None = None) -> str | None:
    from src.services.chat_normalization import normalize_chat_text
    from src.services.answer_evidence import is_maintenance_schedule
    lower = normalize_chat_text(query).lower()
    if is_maintenance_schedule(query):
        return 'official_manual'
    if source_need == 'policy' and any(k in lower for k in ['phí sạc', 'giá sạc', 'biểu phí', 'trạm sạc', 'dịch vụ sạc']):
        return 'official_service'
    if source_need in {'catalog', 'policy', 'manual', 'guide'}:
        return 'official_' + source_need
    if 'bảo hành' in lower:
        return 'official_policy'
    if any(k in lower for k in ['ứng dụng', 'app', 'đăng nhập', 'mật khẩu', 'từ xa']):
        return 'official_guide'
    if re.search(r'mobile\s*service', lower):
        return 'official_guide'
    if any(k in lower for k in ['phí sạc', 'giá sạc', 'biểu phí', 'trạm sạc', 'dịch vụ sạc']):
        return 'official_service'
    if any(k in lower for k in ['ứng dụng', 'app', 'đăng nhập', 'mật khẩu', 'đặt lịch', 'từ xa']):
        return 'official_guide'
    if any(k in lower for k in ['adas', 'ngập nước', 'sổ tay']):
        return 'official_manual'
    if any(k in lower for k in ["các dòng xe", "dòng xe", "các mẫu xe", "mẫu xe", "dải sản phẩm", "danh mục xe", "chi phí lăn bánh", "lăn bánh"]):
        return "official_catalog"
    if "bảo hành" in lower:
        return "official_policy"
    if any(k in lower for k in ["dung lượng", "công suất", "nedc", "quãng đường", "eco", "plus", "thông số"]):
        return "official_catalog"
    if re.search(r'\bmàu\b', lower):
        return 'official_catalog'
    if any(k in lower for k in ["adas", "ngập nước", "sổ tay"]):
        return "official_manual"
    if any(k in lower for k in ["ứng dụng", "app", "đặt lịch", "từ xa"]) and not any(k in lower for k in ["trạm sạc", "sạc pin", "cứu hộ", "bảo dưỡng"]):
        return "official_guide"
    return None


def requires_official_evidence(query: str, source_need: str | None = None) -> bool:
    from src.services.vehicle_knowledge import is_general_vehicle_question
    from src.services.answer_evidence import normalized
    if source_need in {'guide', 'manual', 'policy', 'catalog'}:
        return True
    if not requested_source_type(query):
        return False
    return (not is_general_vehicle_question(query)
            or bool(re.search(r'\b(?:app|ung dung|vinfast|vf\s*(?:[356789]|e34))\b|mobile\s*service', normalized(query))))


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
    verification = PROJECT_ROOT / "docs/data-source-url-verification.json"
    if verification.is_file():
        for item in json.loads(verification.read_text(encoding="utf-8")):
            if item["source_id"] in registry and item["status_code"] == 200:
                date.fromisoformat(item["verified_at"])
                registry[item["source_id"]].setdefault("approved_urls", {})[item["url"]] = item["verified_at"]
    return registry


def valid_citation(citation: dict, model: str | None = None) -> bool:
    source = source_registry().get(citation.get("source_id"))
    if not source:
        return False
    expected_date = source.get("approved_urls", {}).get(citation.get("url"))
    if expected_date is None and source["url"] == citation.get("url"):
        expected_date = source["verified_at"]
    if expected_date is None:
        return False
    if urlparse(citation["url"]).hostname not in {"vinfastauto.com", "om.vinfastauto.com", "shop.vinfastauto.com"}:
        return False
    if citation.get("status_code") != 200 or citation.get("verified_at") != expected_date:
        return False
    normalized = {re.sub(r"\s+", "", str(m)).upper() for m in citation.get("applicable_models", [])}
    normalized_model = re.sub(r"\s+", "", model).upper() if model else None
    if normalized_model and "ALL" not in normalized and normalized_model not in normalized:
        return False
    if not normalized or not citation.get("relevant_snippet"):
        return False
    try:
        dist = float(citation["distance"])
        max_dist = get_settings().rag_max_distance
        if not 0 <= dist <= max_dist:
            return False
    except (KeyError, TypeError, ValueError):
        return False
    return not resolve_policy_conflict(citation["relevant_snippet"])


class RAGService:
    @staticmethod
    def failure(status: str, category: str) -> dict:
        return {"status": status, "best_distance": None, "citations": [],
                "diagnostics": {"stage": "retrieval", "category": category, "status": status.lower(), "candidates": []}}

    def retrieve(self, query: str, top_k: int = 3, vehicle_model: str | None = None, *, cost_subject: str | None = None, source_need: str | None = None) -> dict:
        settings = get_settings()
        from src.services.charging_questions import reviewed_charging_guides
        from src.services.warranty_questions import reviewed_warranty_overviews
        from src.services.reviewed_knowledge import reviewed_maintenance_schedules, reviewed_model_colors
        reviewed = (reviewed_charging_guides(query) or reviewed_warranty_overviews(query, vehicle_model)
                    or reviewed_maintenance_schedules(query, vehicle_model) or reviewed_model_colors(query, vehicle_model))
        if reviewed:
            registry = source_registry()
            citations = []
            for record in reviewed:
                source = registry.get(record['source_id'], {})
                url = record.get('url') or record.get('source_url') or source.get('url')
                verified_at = source.get('approved_urls', {}).get(url) or (
                    source.get('verified_at') if url == source.get('url') else None)
                citations.append({**source, **record, 'url': url, 'verified_at': verified_at,
                                  'applicable_models': record.get('applicable_models', ['ALL']), 'distance': 0.0})
            citations = [citation for citation in citations if valid_citation(citation, vehicle_model)]
            if citations:
                return {'status': 'SUCCESS', 'citations': citations, 'best_distance': 0.0,
                        'diagnostics': {'stage': 'retrieval', 'category': 'verified_public_guide_snapshot'}}
        # The same reviewed facts supply cards and quotes. Unknown/expired prices
        # cannot fall back to an older differently scoped index price.
        from src.services.answer_evidence import normalized
        if cost_subject is None:
            from src.services.conversation_context import cost_subject_for
            cost_subject = cost_subject_for(query)
        technical_terms = {'range': ('quang duong', 'mot lan sac', 'di duoc', 'tam hoat dong', 'tam di chuyen', 'di bao xa', 'driving range', 'published range', 'nedc', 'wltp'),
                           'capacity': ('dung luong', 'battery capacity'), 'power': ('cong suat',),
                           'seats': ('cho ngoi', 'may cho', 'bao nhieu cho', 'seats', 'seating positions'),
                           'charging_time': ('thoi gian sac', 'sac nhanh bao lau', 'sac nhanh mat')}
        technical_keys = [key for key, terms in technical_terms.items() if any(term in normalized(query) for term in terms)]
        requested_models = {'VF' + model.upper() for model in re.findall(r'\bvf\s*(e34|[356789])\b', normalized(query))}
        if vehicle_model and technical_keys and requested_models - {vehicle_model}:
            return self.failure('NO_SOURCE', 'unresolved_catalog_scope')
        if vehicle_model and technical_keys and re.search(
                r'real.world|actual range|thuc te|cho day|tai trong|full load|towing|winter|freezing|nhiet do|temperature', normalized(query)):
            return self.failure('NO_SOURCE', 'unresolved_catalog_conditions')
        purpose = requested_source_type(query, source_need=source_need)
        published_charging_time = technical_keys == ['charging_time'] and not re.search(
            r'huong dan|cach|thao tac|bao loi|khong sac|nguy hiem', normalized(query))
        if vehicle_model and technical_keys and (purpose == 'official_catalog' or published_charging_time):
            from src.services.vehicle_catalog import catalog_cards, catalog_citations, requested_variants
            variants = requested_variants(normalized(query), vehicle_model, True)
            cards = catalog_cards([vehicle_model])
            if variants:
                cards = [card for card in cards if card.variant in variants]
            shared_time = (published_charging_time and cards and all(card.fast_charge_time for card in cards)
                           and len({card.fast_charge_time for card in cards}) == 1)
            if not cards or len(cards) > top_k or (len(cards) > 1 and not variants and not shared_time):
                return self.failure('NO_SOURCE', 'unresolved_catalog_scope')
            citations = []
            for card, citation in zip(cards, catalog_citations(cards), strict=True):
                scope = citation['fact_scope']
                requested_cycles = {value.upper() for value in re.findall(r'\b(?:nedc|wltp)\b', normalized(query))}
                if 'range' in technical_keys and requested_cycles and requested_cycles != {scope.get('range_standard')}:
                    return self.failure('NO_SOURCE', 'unresolved_catalog_conditions')
                if 'charging_time' in technical_keys:
                    requested_soc = re.findall(r'(\d+)\s*%', query)
                    interval = re.search(r'(?:tu|from)\s*(\d+)\s*%?\s*(?:den|to|[-–])\s*(\d+)\s*%', normalized(query))
                    if interval:
                        requested_soc = list(interval.groups())
                    source_soc = re.findall(r'(\d+)\s*%', card.fast_charge_time or '')
                    if ((requested_soc and requested_soc != source_soc)
                            or re.search(r'\d[\d.,]*\s*kw\b', normalized(query))):
                        return self.failure('NO_SOURCE', 'unresolved_catalog_conditions')
                if re.search(r'\b20\d{2}\b', query) and str(scope.get('model_year')) not in query:
                    return self.failure('NO_SOURCE', 'unresolved_catalog_scope')
                fields = [spec.label + ': ' + spec.value for spec in card.specs
                          if any(any(term in normalized(spec.label) for term in technical_terms[key]) for key in technical_keys)]
                if 'capacity' in technical_keys and card.battery_capacity:
                    fields.append('Dung lượng pin khả dụng: ' + card.battery_capacity)
                if not fields or len(fields) < len(technical_keys):
                    return self.failure('NO_SOURCE', 'missing_catalog_fact')
                snippet = '\n'.join(card.name + (' ' + scope['drivetrain'] if scope.get('drivetrain') else '')
                                    + ': ' + field for field in fields)
                candidate = {**citation, 'relevant_snippet': snippet, 'distance': 0.0}
                if valid_citation(candidate, vehicle_model):
                    citations.append(candidate)
            if len(citations) != len(cards):
                return self.failure('NO_SOURCE', 'unverified_catalog_fact')
            if sum(utf8_size(c['relevant_snippet']) for c in citations) > settings.rag_context_max_bytes:
                return self.failure('NO_SOURCE', 'context_budget_exceeded')
            return {'status': 'SUCCESS', 'citations': citations, 'best_distance': 0.0,
                    'diagnostics': {'stage': 'retrieval', 'category': 'verified_catalog_fact_snapshot'}}
        if vehicle_model and cost_subject == 'vehicle_purchase':
            from src.services.vehicle_catalog import public_price_snapshots, requested_variants
            records = public_price_snapshots()
            if records:
                variants = requested_variants(normalized(query), vehicle_model, True)
                evidence = []
                for record in records:
                    if record.get('model') != vehicle_model or variants and record.get('variant') not in variants:
                        continue
                    if record.get('price_vnd') is None:
                        continue
                    if re.search(r'\b20\d{2}\b', query) and str(record.get('model_year')) not in query:
                        continue
                    age = (date.today() - date.fromisoformat(record['verified_at'])).days
                    if not 0 <= age <= 7:
                        continue
                    citation = {**source_registry().get(record['source_id'], {}), **record,
                                'applicable_models': [record['model']], 'distance': 0.0}
                    if valid_citation(citation, vehicle_model):
                        evidence.append(citation)
                if evidence:
                    return {'status': 'SUCCESS', 'citations': evidence[:top_k], 'best_distance': 0.0,
                            'diagnostics': {'stage': 'retrieval', 'category': 'verified_public_price_snapshot'}}
                return self.failure('NO_SOURCE', 'no_current_scoped_price')
        if not Path(settings.chroma_persist_dir, "chroma.sqlite3").is_file():
            return self.failure("UNAVAILABLE", "missing_index")
        try:
            collection = get_collection(settings.chroma_persist_dir)
            count = collection.count()
            if not count:
                return self.failure("NO_SOURCE", "empty_collection")
            candidates = 20
            source_type = requested_source_type(query, source_need=source_need)
            registry = source_registry()
            eligible_types = {source_type}
            if source_need == 'policy' or source_type == 'official_service':
                eligible_types.update({'official_policy', 'official_service'})
            allowed = [source_id for source_id, meta in registry.items() if meta["source_type"] in eligible_types] if source_type else []
            if not allowed:
                # Source title relevance narrows service queries without benchmark IDs.
                scores = {source_id: len(words(query) & words(meta["title"])) for source_id, meta in registry.items()}
                peak = max(scores.values(), default=0)
                allowed = [source_id for source_id, score in scores.items() if peak >= 2 and score == peak]
            where = {"source_id": {"$in": allowed}} if allowed else None
            configuration = collection.configuration
            if configuration.get("hnsw", {}).get("space") == "l2" and configuration.get("embedding_function"):
                # Full lexical candidate selection keeps Vietnamese terms that a
                # vector-only shortlist misses. Distances remain the actual stored
                # embedding's squared L2, with the same conservative threshold.
                import numpy as np
                corpus = get_corpus(settings.chroma_persist_dir, count)
                function = configuration["embedding_function"]
                query_embedding = function.embed_query(input=[query])[0] if hasattr(function, "embed_query") else function(input=[query])[0]
                distances = np.sum((np.asarray(corpus["embeddings"]) - query_embedding) ** 2, axis=1)
                rows = [(doc, meta, float(distance), chunk_id) for doc, meta, distance, chunk_id in zip(
                    corpus["documents"], corpus["metadatas"], distances, corpus["ids"], strict=True
                ) if (not allowed or meta.get("source_id") in allowed) and model_applies(meta or {}, vehicle_model)]
                ranked = rank_candidates(query, rows)
                # Do not lose supported candidates behind high-distance lexical hits.
                cutoff = settings.rag_max_distance
                shortlist = [row for row in ranked if row[2] <= cutoff][:candidates]
                shortlist += [row for row in ranked if row[2] > cutoff][:max(0, candidates - len(shortlist))]
                result = {"documents": [[r[0] for r in shortlist]], "metadatas": [[r[1] for r in shortlist]], "distances": [[r[2] for r in shortlist]], "ids": [[r[3] for r in shortlist]]}
            else:
                # Chroma stores comma-separated model applicability; fetch the
                # source subset first and normalize before the bounded shortlist.
                raw = collection.query(query_texts=[query], n_results=count, where=where, include=["documents", "metadatas", "distances"])
                indices = [i for i, meta in enumerate(raw["metadatas"][0]) if model_applies(meta or {}, vehicle_model)][:candidates]
                result = {key: [[raw[key][0][i] for i in indices]] for key in ["documents", "metadatas", "distances", "ids"]}
            from src.services.rag_index import load_parent_map
            max_limit = 4 if any(c in query.lower() for c in [",", " và ", "đồng thời", "biểu phí", "tính năng"]) else 3
            return self.filter_results(result, vehicle_model, query, min(max(1, top_k), max_limit), parent_map=load_parent_map(settings.chroma_persist_dir))
        except TimeoutError:
            return self.failure("TIMEOUT", "timeout")
        except Exception as error:
            from chromadb.errors import NotFoundError
            if isinstance(error, NotFoundError):
                return self.failure("UNAVAILABLE", "missing_collection")
            return self.failure("ERROR", "backend_or_schema_error")

    def retrieve_diagnostics(self, query: str, top_k: int = 3, vehicle_model: str | None = None) -> dict:
        return self.retrieve(query, top_k, vehicle_model)

    def filter_results(self, result: dict, vehicle_model: str | None = None, query: str = "", top_k: int = 3, *, parent_map: dict | None = None) -> dict:
        registry = source_registry()
        citations = []
        diagnostics = []
        initial_budget = get_settings().rag_context_max_bytes
        budget = initial_budget
        candidates = list(zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0], result["ids"][0], strict=True
        ))
        candidates = rank_candidates(query, candidates) if query else candidates
        accepted_parents = set()
        for doc, meta, distance, chunk_id in candidates:
            meta = meta or {}
            parent_id = meta.get("parent_chunk_id")
            if parent_id:
                if not parent_map or parent_id not in parent_map:
                    raise ValueError("Missing parent evidence")
                parent = parent_map[parent_id]
                from src.services.rag_index import content_hash
                child_hash = content_hash(doc)[:12]
                if meta.get("parent_sha256") != parent.get("sha256") or not re.fullmatch(
                    re.escape(parent_id) + r"::child:\d+:" + child_hash, chunk_id
                ):
                    raise ValueError("Child-parent integrity mismatch")
                doc, meta = parent["document"], parent["metadata"]
                if parent_id in accepted_parents:
                    continue
            source = registry.get(meta.get("source_id"))
            approved_date = source.get("approved_urls", {}).get(meta.get("url")) if source else None
            if not source or (source["url"] != meta.get("url") and not approved_date):
                diagnostics.append({"chunk_id": chunk_id, "reason": "registry_mismatch"})
                continue
            models = meta.get("applicable_models", "")
            models = models.split(",") if isinstance(models, str) else models
            models = [re.sub(r"\s+", "", str(m)).upper() for m in models]
            if vehicle_model and "ALL" not in models and re.sub(r"\s+", "", vehicle_model).upper() not in models:
                diagnostics.append({"chunk_id": chunk_id, "reason": "model_mismatch"})
                continue
            if meta.get('reviewed_scope_json'):
                from src.services.answer_evidence import normalized as fold_scope
                try:
                    scope = json.loads(meta['reviewed_scope_json'])
                    if not isinstance(scope, dict):
                        raise ValueError('Invalid reviewed scope')
                except (ValueError, TypeError):
                    diagnostics.append({'chunk_id': chunk_id, 'reason': 'invalid_reviewed_scope'})
                    continue
                body = fold_scope(query)
                years = set(re.findall(r'\b20\d{2}\b', body))
                trims = set(re.findall(r'\b(?:eco|plus|awd|fwd)\b', body))
                commercial = bool(re.search(r'thuong mai|chay dich vu', body))
                severe = 'khac nghiet' in body
                if ((years and years != {str(scope.get('model_year'))})
                        or (trims and not trims <= set(str(scope.get('variant') or '').replace('-', ' ').split()))
                        or (commercial and scope.get('usage') != 'commercial')
                        or (severe and scope.get('usage') != 'severe')):
                    diagnostics.append({'chunk_id': chunk_id, 'reason': 'unresolved_reviewed_scope'})
                    continue
            variant = re.search(r"\b(plus|eco)\b", query, re.I)
            if (meta.get('catalog_scope') == 'model_colors'
                    and re.search(r'nội thất|noi that', query, re.I)
                    and not re.search(r'nội thất|noi that', doc or '', re.I)):
                diagnostics.append({'chunk_id': chunk_id, 'reason': 'missing_answer_subject'})
                continue
            model_colors = (meta.get('catalog_scope') == 'model_colors'
                            and re.search(r'\bm(?:à|a)u\b', query, re.I)
                            and not re.search(r'\b(?:plus|eco)\b', doc or '', re.I))
            if variant and source["source_type"] == "official_catalog" and not model_colors and variant.group().lower() not in (doc or "").lower():
                diagnostics.append({"chunk_id": chunk_id, "reason": "variant_mismatch"})
                continue
            sections = select_supported_evidence(query, [{**source, "catalog_scope": meta.get('catalog_scope'),
                                                         "relevant_snippet": doc or ""}])
            if not sections:
                reason = "procedure_goal_mismatch" if "đặt lịch" in query.casefold() and "đặt lịch" not in (doc or "").casefold() else "missing_answer_evidence"
                diagnostics.append({"chunk_id": chunk_id, "reason": reason})
                continue
            excerpt = sections[0]["relevant_snippet"]
            lower_query = query.casefold()
            lower_excerpt = re.sub(r"\s*-\s*", " ", excerpt.casefold())
            subjects = [term for term in ("truyền động", "pin cao áp", "ắc quy", "lốp", "mobile service", "ngập nước", "adas") if term in lower_query]
            if any(term not in lower_excerpt for term in subjects) or (query and (not words(query) & words(excerpt) or len(words(excerpt)) < 6)):
                diagnostics.append({"chunk_id": chunk_id, "reason": "missing_answer_subject"})
                continue
            from src.services.answer_evidence import is_maintenance_schedule
            procedure_requested = (not is_maintenance_schedule(query)
                                   and any(term in lower_query for term in ("hướng dẫn", "cách ", "làm thế nào", "như thế nào")))
            body = "\n".join(excerpt.splitlines()[1:]).casefold()
            if procedure_requested and "đặt lịch" in lower_query and "đặt lịch" not in excerpt.splitlines()[0].casefold():
                diagnostics.append({"chunk_id": chunk_id, "reason": "procedure_goal_mismatch"})
                continue
            is_pricing_or_policy = any(term in lower_query for term in ("biểu phí", "phí", "giá", "chi phí", "chính sách")) and any(term in excerpt.casefold() for term in ("đơn giá", "biểu phí", "phí sử dụng", "chính sách", "giá sạc", "vnđ", "đồng/phút"))
            if procedure_requested and not is_pricing_or_policy and not any(term in body for term in ("bước ", "bấm ", "chọn ", "nhập ", "truy cập ", "thực hiện ", "kiểm tra ", "xác nhận ", "bật ", "tắt ")):
                diagnostics.append({"chunk_id": chunk_id, "reason": "missing_procedure"})
                continue
            if source["source_type"] == "official_catalog":
                passage_variants = set(re.findall(r"\b(?:eco|plus)\b", excerpt.lower()))
                years = set(re.findall(r"\b20\d{2}\b", excerpt))
                requested_years = set(re.findall(r"\b20\d{2}\b", query))
                is_catalog_overview = any(term in query.casefold() for term in ("các dòng xe", "dòng xe", "các mẫu xe", "mẫu xe", "dải sản phẩm", "danh mục xe", "lăn bánh"))
                if not is_catalog_overview and ((passage_variants and not variant) or (variant and not model_colors and passage_variants != {variant.group().lower()}) or (requested_years and not requested_years <= years)):
                    diagnostics.append({"chunk_id": chunk_id, "reason": "unresolved_applicability"})
                    continue
            if utf8_size(excerpt) > budget:
                diagnostics.append({"chunk_id": chunk_id, "reason": "context_budget_exceeded", "size_bytes": utf8_size(excerpt)})
                continue
            snippet = excerpt
            citation = {
                **source,
                "url": meta["url"],
                "verified_at": approved_date or source["verified_at"],
                "source_id": meta["source_id"],
                "chunk_id": chunk_id,
                "applicable_models": models,
                "relevant_snippet": snippet,
                "distance": distance,
            }
            if parent_id:
                citation["parent_chunk_id"] = parent_id
            if model_colors:
                citation['catalog_scope'] = 'model_colors'
            if not valid_citation(citation, vehicle_model):
                reason = "unsafe_content" if resolve_policy_conflict(snippet) else "distance_or_metadata"
                diagnostics.append({"chunk_id": chunk_id, "source_id": meta["source_id"], "distance": distance, "reason": reason})
                continue
            diagnostics.append({"chunk_id": chunk_id, "source_id": meta["source_id"], "distance": distance, "reason": "accepted"})
            citations.append(citation)
            accepted_parents.add(parent_id or chunk_id)
            budget -= utf8_size(snippet)
            if len(citations) >= top_k or budget <= 0:
                break
        return {
            "status": "SUCCESS" if citations else "NO_SOURCE",
            "citations": citations,
            "best_distance": min(c["distance"] for c in citations) if citations else None,
            "diagnostics": {"stage": "retrieval", "candidates": diagnostics,
                            "candidate_parent_ids": list(dict.fromkeys((m or {}).get("parent_chunk_id", cid) for _, m, _, cid in candidates)),
                            "selected_parent_ids": [c.get("parent_chunk_id", c["chunk_id"]) for c in citations],
                            "embedding": "collection-configured", "distance_threshold": get_settings().rag_max_distance,
                            "category": "success" if citations else "context_budget_exceeded" if any(d["reason"] == "context_budget_exceeded" for d in diagnostics) else "no_eligible_evidence",
                            "context_bytes_used": initial_budget - budget, "context_bytes_remaining": budget, "context_max_bytes": initial_budget},
        }


rag_service = RAGService()
