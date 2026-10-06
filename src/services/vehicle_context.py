"""Session vehicle references, kept separate from confirmed incident facts."""
import re

from src.agents.guardrails import sanitize_pii
from src.agents.nodes.triage_node import classify_request_kind, extract_fields
from src.services.chat_classification import denied_reports, temporal_context
from src.services.vehicle_knowledge import is_vehicle_comparison

MODEL = re.compile(r"\b(?:vf\s*(?:e34|[356789])|e34)\b", re.I)


def resolve_vehicle_context(text: str, previous: dict | None = None) -> dict:
    previous = previous or {}
    text = sanitize_pii(text)[0]
    lower = text.casefold().strip(" .?!")
    models = list(dict.fromkeys(
        "e34" if "e34" in match.casefold() else re.sub(r"\s+", "", match).upper()
        for match in MODEL.findall(text)
    ))
    negated_models = set(
        "e34" if "e34" in m.casefold() else re.sub(r"\s+", "", m).upper()
        for m in re.findall(r"(?:không phải|khong phai|chứ không phải|chu khong phai)\s+(vf\s*(?:[356789]|e34)|e34)", lower)
    )
    models = [m for m in models if m not in negated_models]
    request_kind = classify_request_kind(text)
    failure = request_kind == "incident" and temporal_context(text) not in {'resolved_past', 'hypothetical', 'knowledge'}
    extracted = extract_fields(text)
    new_scope = temporal_context(text) not in {'hypothetical', 'knowledge', 'resolved_past'} and bool(re.search(
        r'(?:xe\s+(?:vf\s*(?:[356789]|e34)|e34)?\s*khác|sự cố (?:khác|mới)|vụ (?:khác|mới))', lower))
    scope = int(previous.get('incident_scope', 1)) + int(new_scope)
    owned = previous.get("owned_model")
    ownership_clause = ""
    for clause in re.split(r"[,.;!?]+", lower):
        if re.search(
            r"(?:xe\s+.*của (?:tôi|mình)|(?:tôi|mình)\s+(?:đang\s+)?(?:sử dụng|sở hữu|có xe)|"
            r"(?:tôi|mình)\s+đang\s+(?:đi|lái)\s+(?:xe\s+)?(?:vf|e34))",
            clause,
        ):
            ownership_clause = clause
            break
    ownership = bool(ownership_clause) and not any(
        term in ownership_clause for term in ("nếu", "giả sử", "lái thử", "đi xem", "muốn", "dự định", "neu", "gia su", "lai thu", "di xem", "muon", "du dinh")
    )
    incident_model = None if new_scope else previous.get("incident_model")
    if incident_model in negated_models:
        incident_model = None
    if ownership and len(models) == 1:
        owned = models[0]
        incident_model = None
    model_answer = bool(previous.get("is_incident") and MODEL.fullmatch(lower))
    slot_answer = bool(previous.get("is_incident") and request_kind == "uncertain"
                       and extracted and not lower.startswith(("còn ", "thế còn ", "vậy còn ")))
    incident_fields = dict(previous.get("incident_fields", {})) if (previous.get("is_incident") or previous.get("owned_model")) and not new_scope else {}
    for denied in denied_reports(text):
        for field, value in extract_fields(denied, asserted_only=False).items():
            if str(incident_fields.get(field, '')).casefold() == value.casefold():
                incident_fields.pop(field, None)

    soc_match = re.search(r"(?:pin\s*(?:còn)?\s*|pin\s*)(\d{1,3}%)|\b(\d{1,3}%)\s*pin", lower)
    if soc_match:
        incident_fields["soc"] = soc_match.group(1) or soc_match.group(2)
    contact_match = re.search(r"\b(?:liên hệ|goi lai|lien he)\s+(?:sau|truoc|vao lúc)?\s*(\d{1,2}(?:h| giờ|:00)?)\b", lower)
    if contact_match:
        incident_fields["contact_preference"] = f"sau {contact_match.group(1)}" if "sau" in lower else contact_match.group(0)
    safety_update = bool(previous.get("is_incident") and re.search(r"\b(an toàn|an toan|đã dừng|da dung)\b", lower))
    if safety_update:
        incident_fields["safety_status"] = "customer_reported_safe"

    prior_topic = previous.get("topic", "")
    symbol_reference = bool(
        re.search(r'(?:biểu tượng này|sự cố này|lỗi này|đây này|đèn này)', lower)
        and re.search(r'rùa|con rùa', prior_topic, re.I)
    )
    incident = (
        failure
        or model_answer
        or slot_answer
        or safety_update
        or bool(previous.get("is_incident") and soc_match)
        or symbol_reference
    )

    if incident:
        incident_fields.update(extracted)
        incident_model = models[0] if len(models) == 1 else (incident_model or owned)
        models = [incident_model] if incident_model else []
    elif not models:
        models = list(previous.get("models", []))

    resolved = text
    if symbol_reference:
        incident_fields['warning_symbol'] = 'rùa vàng'
        resolved = f'{text} (rùa vàng)'
    topic = MODEL.sub("", text).strip(" .?!")
    # Only bounded references inherit a topic; full questions start a new topic.
    switch = bool(re.fullmatch(r"(?:(?:còn|thế còn|vậy còn)\s+)?(?:vf\s*(?:e34|[356789])|e34)(?:\s+thì sao)?", lower))
    followup = lower in {
        "pin thì sao", "còn pin", "pin", "bao lâu", "bao nhiêu", "điều kiện là gì",
        "điều kiện gì", "ở đâu", "cần gì", "làm thế nào",
    }
    if prior_topic and not incident and (switch or followup):
        topic = prior_topic
        if "pin" in lower and "pin" not in topic.casefold():
            topic = f"{topic} — pin"
        resolved = f"{topic} {' và '.join(models)}: {text}"

    if model_answer or slot_answer:
        resolved = f"{previous.get('incident_query', '')} {text}".strip()
    return {
        "models": models,
        "incident_scope": scope,
        "scope_changed": new_scope,
        "incident_case_id": None if new_scope else previous.get('incident_case_id'),
        "topic": topic[:800],
        "incident_query": resolved[:1200] if incident else previous.get("incident_query", ""),
        "incident_fields": incident_fields if (incident or incident_fields) else previous.get("incident_fields", {}),
        "owned_model": owned,
        "incident_model": incident_model or previous.get("incident_model"),
        "is_incident": False if is_vehicle_comparison(text) else (incident or previous.get("is_incident", False)),
        "resolved_query": resolved[:1200],
        "source": "customer_message" if MODEL.search(text) else "session_reference",
        "model_source": text[:500] if MODEL.search(text) else previous.get("model_source"),
    }


def detect_memory_recall_query(query: str, vehicle_context: dict) -> tuple[bool, str | None]:
    lower = query.lower()
    from src.agents.guardrails import strip_accents
    lower_unaccented = strip_accents(lower)

    is_recall = bool(
        re.search(r"\b(?:quay lại|nhắc lại|vừa rồi|trước đó|xe tôi là dòng nào|pin còn bao nhiêu)\b", lower)
        or re.search(r"\b(?:quay lai|nhac lai|vua roi|truoc do|xe toi la dong nao|pin con bao nhieu)\b", lower_unaccented)
    )
    if not is_recall:
        return False, None

    incident_model = vehicle_context.get("incident_model") or vehicle_context.get("owned_model")
    fields = vehicle_context.get("incident_fields", {})
    soc = fields.get("soc")

    if incident_model or soc:
        parts = []
        if incident_model:
            parts.append(f"{incident_model}")
        if soc:
            parts.append(f"pin còn {soc}")
        details = " và ".join(parts)
        answer = f"Dạ xe anh/chị đang ghi nhận sự cố là {details} ạ. Anh/chị cần em hỗ trợ tiếp điều gì cho xe ạ?"
        return True, answer

    return False, None
