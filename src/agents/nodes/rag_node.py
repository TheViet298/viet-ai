from __future__ import annotations

import asyncio
import re
import time

from pydantic import BaseModel, Field

from src.agents.context_manager import build_7_layer_context, load_prompt, resolve_policy_conflict, trim_context_layers
from src.agents.guardrails import sanitize_pii
from src.agents.state import AgentState
from src.agents.tools.vinfast_tools import vinfast_manual_search
from src.config import get_settings
from src.services.agent_llm import structured_call
from src.services.answer_evidence import AnswerClaim, canonical_answer_claim, extract_numeric_claims, has_color_evidence, is_color_question, is_turtle_question, normalized, validate_answer_claims
from src.services.observability import observation, update_observation
from src.services.rag_service import RAGService, select_supported_evidence, valid_citation


class GroundedAnswer(BaseModel):
    answer: str = Field(max_length=3000)
    source_ids: list[str]
    supported: bool
    claims: list[AnswerClaim] = Field(default_factory=list)


async def rag_node(state: AgentState) -> dict:
    query = state.get("resolved_query") or state.get("latest_user_message", "")
    from src.services.faq_questions import faq_parts, vehicle_models
    from src.services.agent_llm import new_turn_budget
    from src.agents.guardrails import strip_accents
    state.setdefault('llm_budget', new_turn_budget(time.monotonic() + get_settings().agent_turn_timeout_s))
    unsupported = any(term in strip_accents(query.casefold()) for term in (
        'bi mat', 'noi bo', 'thang sau', 'khong cong khai', 'chua cong khai'))
    parts = [] if unsupported or state.get('_faq_subquestion') else faq_parts(query)
    warranty_parts = any(label == 'Bảo hành pin' for label, _, _ in parts)
    if parts:
        sections, results, citations = [], [], []
        for label, subquery, source_need in parts:
            understanding = {**(state.get('turn_understanding') or {}), 'source_need': source_need,
                             'cost_subject': 'charging' if label == 'Biểu phí sạc' else None}
            local_models = vehicle_models(subquery)
            part_model = local_models[0] if len(local_models) == 1 else (
                None if len(vehicle_models(query)) > 1 else state.get('vehicle_model'))
            result = await rag_node({**state, 'resolved_query': subquery, 'turn_understanding': understanding,
                                     'vehicle_model': part_model, '_faq_subquestion': True})
            results.append(result)
            body = result.get('response', '').removeprefix('Theo tài liệu VinFast:\n\n')
            if label == 'Biểu phí sạc' and result.get('rag_citations'):
                body = '\n\n'.join('- ' + line for line in body.splitlines() if line.strip())
                dates = sorted({c['verified_at'] for c in result['rag_citations']})
                body += '\n\nĐây là mức phí trong tài liệu đã xác minh ngày ' + ', '.join(dates) + '. Cần kiểm tra biểu phí và ưu đãi áp dụng cho xe trên ứng dụng trước khi sạc.'
            sections.append(f'### {label}\n\n{body}')
            for citation in result.get('rag_citations', []):
                if citation not in citations:
                    citations.append(citation)
        prefix = 'Theo tài liệu VinFast:' if citations else 'Em chưa tìm được đủ nguồn cho các phần sau:'
        reply = prefix + '\n\n' + '\n\n'.join(sections)
        if warranty_parts:
            reply += ('\n\nQuý khách cho biết dòng xe, đời xe, số km hiện tại và xe có từng chạy dịch vụ hay không '
                      'để em đối chiếu thời hạn bảo hành pin và lịch bảo dưỡng đúng xe nhé.')
        statuses = [('SUCCESS' if not result.get('is_no_source') else
                     'TIMEOUT' if result.get('retrieval_status') == 'TIMEOUT' else
                     'ERROR' if result.get('retrieval_status') in {'ERROR', 'UNAVAILABLE'} else 'NO_SOURCE')
                    for result in results]
        answer_status = ('answered' if all(status == 'SUCCESS' for status in statuses) else
                         'partial' if any(status == 'SUCCESS' for status in statuses) else
                         'error' if any(status in {'ERROR', 'TIMEOUT'} for status in statuses) else 'needs_data')
        return {'is_no_source': not bool(citations), 'is_rag_query': True,
                'answer_status': answer_status,
                'retrieval_status': ('PARTIAL' if any(r.get('is_no_source') for r in results) else 'SUCCESS') if citations else 'NO_SOURCE',
                'retrieval_diagnostics': {'category': 'compound_warranty_maintenance' if warranty_parts else 'compound_charging', 'parts': [
                    {'label': part[0], 'status': status,
                     'source_ids': list(dict.fromkeys(c['source_id'] for c in result.get('rag_citations', []))),
                     'diagnostics': result.get('retrieval_diagnostics', {})}
                    for part, result, status in zip(parts, results, statuses, strict=True)]},
                'rag_citations': citations, 'rag_context': [c['relevant_snippet'] for c in citations],
                'answer_claims': [claim for result in results for claim in result.get('answer_claims', [])],
                'needs_staff_review': any(result.get('is_no_source') for result in results),
                'response_type': 'FAQ_ANSWER', 'response': reply, 'final_response': reply}
    remaining = state.get("llm_budget", {}).get("deadline", time.monotonic() + get_settings().agent_turn_timeout_s) - time.monotonic()
    retrieval = RAGService.failure("NO_SOURCE", "unsupported_request") if unsupported else RAGService.failure("TIMEOUT", "deadline_exhausted")
    if not unsupported and remaining > 0:
        try:
            search_query = query + " chỉ báo giới hạn công suất" if is_turtle_question(query) else query
            with observation('retrieval', as_type='retriever', metadata={'layer': 'retrieval',
                    'timeout_s': min(remaining, get_settings().rag_retrieval_timeout_s),
                    'timeout_source': 'turn_deadline' if remaining <= get_settings().rag_retrieval_timeout_s else 'retrieval_limit'}) as span:
                understanding = state.get('turn_understanding') or {}
                purpose = {key: understanding[key] for key in ('cost_subject', 'source_need') if understanding.get(key)}
                retrieval = await asyncio.wait_for(vinfast_manual_search(search_query, vehicle_model=state.get("vehicle_model"), **purpose),
                                                   timeout=min(remaining, get_settings().rag_retrieval_timeout_s))
                update_observation(span, output={'status': retrieval.get('status'),
                                                 'source_count': len(retrieval.get('citations', [])),
                                                 'source_ids': [c.get('source_id') for c in retrieval.get('citations', [])]})
        except TimeoutError:
            retrieval = RAGService.failure("TIMEOUT", "timeout")
        except Exception:
            retrieval = RAGService.failure("ERROR", "retrieval_tool_error")
    citations = [c for c in retrieval.get("citations", []) if valid_citation(c, state.get("vehicle_model"))]
    citations = select_supported_evidence(query, citations)
    color_snapshot = []
    if (state.get('turn_understanding') or {}).get('goal') == 'appearance' or is_color_question(query):
        color_snapshot = [c for c in citations if has_color_evidence(c)]
        # Color entities are rendered verbatim from qualifying evidence. Empty
        # generated claims must never let specs become a fabricated color list.
        citations = color_snapshot
    if citations:
        layers = build_7_layer_context({**state, "rag_citations": citations}, load_prompt("rag_qa"))
        try:
            messages = trim_context_layers(layers, max_bytes=get_settings().agent_context_max_bytes)
            if not any(layers.retrieval_context in str(m.content) for m in messages):
                raise ValueError("Evidence cannot fit prompt budget")
        except ValueError:
            citations = []
            retrieval = {**retrieval, "status": "NO_SOURCE", "citations": [], "diagnostics": {
                **retrieval.get("diagnostics", {}), "category": "context_budget_exceeded", "stage": "prompt",
                "selected_parent_ids": [], "prompt_max_bytes": get_settings().agent_context_max_bytes}}
    reply = "Em chưa tìm được tài liệu chính thức đủ để xác nhận thông tin này. Quý khách có thể liên hệ chuyên viên VinFast để đối chiếu."
    if "điều kiện" in query.casefold() and "bảo hành" in query.casefold():
        reply = "Em chưa có đủ thông tin để xác nhận điều kiện bảo hành này. Quý khách có thể liên hệ chuyên viên VinFast, cung cấp đời xe và hạng mục cần bảo hành để đối chiếu."
    if retrieval.get("status") in {"UNAVAILABLE", "ERROR", "TIMEOUT"}:
        reply = "Em chưa tra cứu được thông tin này. Quý khách vui lòng thử lại hoặc liên hệ chuyên viên VinFast để được hỗ trợ."
    elif retrieval.get("diagnostics", {}).get("category") == "context_budget_exceeded":
        reply = "Em chưa đối chiếu đủ các điều kiện để xác nhận thông tin này. Quý khách có thể liên hệ chuyên viên VinFast để được kiểm tra đầy đủ."
    tariff_snapshot = [c for c in citations if c.get('source_type') == 'official_service'
                       and re.search(r'\d[\d.,]*\s*(?:vnđ|vnd|đồng)/(?:kwh|phút)', c['relevant_snippet'], re.I)] if any(
                           term in normalized(query) for term in ('bieu phi', 'phi sac', 'gia sac')) else []
    if tariff_snapshot:
        # Keep rates, session-completion condition and minute tiers together.
        citations = tariff_snapshot
    generated = None
    if citations and state.get("confidence_score", 0) >= 0.60:
        public_snapshot = bool(color_snapshot or tariff_snapshot) or retrieval.get('diagnostics', {}).get('category') in {
            'verified_public_price_snapshot', 'verified_catalog_fact_snapshot', 'verified_public_guide_snapshot'}
        generated = None if public_snapshot else await structured_call({**state, "rag_citations": citations}, "rag_qa", GroundedAnswer)
        if generated is None and get_settings().agent_llm_enabled and not public_snapshot:
            citations = []
            reply = "Em chưa hoàn tất được việc tạo câu trả lời từ tài liệu đã tìm thấy. Quý khách vui lòng thử lại; em chưa thể xác nhận nội dung lúc này."
            retrieval = {**retrieval, "status": "ERROR", "diagnostics": {
                **retrieval.get("diagnostics", {}), "stage": "generation", "category": "generation_unavailable"}}
        if generated and (
            not generated.supported
            or not generated.answer.strip()
            or not generated.source_ids
            or not set(generated.source_ids).issubset({c["source_id"] for c in citations})
            or resolve_policy_conflict(generated.answer)
        ):
            citations = []
            retrieval = {**retrieval, "status": "NO_SOURCE", "diagnostics": {
                **retrieval.get("diagnostics", {}), "stage": "generation", "category": "unsupported_answer"}}
    else:
        citations = []
    # Validate against exactly the evidence the customer will see. Keep distinct
    # snippets from a shared document; deduplicate only identical evidence.
    if generated:
        citations = [c for c in citations if c['source_id'] in generated.source_ids]
    final_citations, seen = [], set()
    for citation in citations:
        citation = {**citation, 'relevant_snippet': sanitize_pii(citation['relevant_snippet'])[0]}
        key = (citation['source_id'], citation.get('url'), citation['relevant_snippet'])
        if key not in seen:
            final_citations.append(citation)
            seen.add(key)
    citations = final_citations
    claim_check = {'supported': True, 'conflicts': []}
    answer_claims = []
    if citations:
        candidate = sanitize_pii(generated.answer)[0] if generated else '\n\n'.join(c['relevant_snippet'] for c in citations)
        fact_context = (state.get('conversation_context') or {}).get('facts', {})
        version = (fact_context.get('version') or {}).get('value') or ''
        subject = f'{state.get("vehicle_model") or ""} {version}'.strip()
        if 'bảo hành' in query.casefold() and 'pin' in query.casefold():
            subject += ' ' + ((fact_context.get('component') or {}).get('value') or ('pin cao áp' if 'pin cao áp' in query.casefold() else 'pin'))
        # Missing values are not factual claims. Numeric statements in the answer
        # are still extracted below, so a placeholder cannot hide an invented number.
        declared_claims = [canonical_answer_claim(c) for c in (generated.claims if generated else [])
                           if normalized(c.value) not in {'', 'khong xac dinh', 'khong ap dung', 'khong co thong tin',
                                                          'n/a', 'not applicable', 'unknown', 'not specified'}]
        answer_claims = [*declared_claims,
                         *extract_numeric_claims(candidate, citations, subject, query)]
        prior = [AnswerClaim.model_validate(c) for entry in (state.get('conversation_context') or {}).get('last_answer', [])
                 for c in entry.get('claims', [])]
        claim_check = validate_answer_claims(answer_claims, citations, prior)
        if not claim_check['supported']:
            citations = []
            from src.services.answer_evidence import numeric_value
            numeric_failure = any(numeric_value(c['value']) is not None or bool(c.get('unit'))
                                  for c in claim_check['unsupported_claims'])
            reply = ('Em chưa xác minh được thông tin này từ tài liệu phù hợp với yêu cầu của Quý khách. Cần đối chiếu thêm với VinFast trước khi sử dụng thông tin này.'
                     if numeric_failure else 'Em chưa có đoạn tài liệu đủ để xác nhận tính năng hoặc các bước thao tác đang hỏi. Cần đối chiếu hướng dẫn chính thức trước khi thực hiện.')
            retrieval = {**retrieval, 'status': 'NO_SOURCE', 'diagnostics': {
                **retrieval.get('diagnostics', {}), 'category': 'unsupported_numeric_claim' if numeric_failure else 'unsupported_textual_claim', 'claim_check': claim_check}}
    if not citations:
        if retrieval.get("status") == "SUCCESS":
            retrieval = {**retrieval, "status": "NO_SOURCE", "diagnostics": {
                **retrieval.get("diagnostics", {}), "category": "missing_answer_evidence"}}
        if is_turtle_question(query) and retrieval.get("status") == "NO_SOURCE":
            reply = "Em chưa tìm được đoạn tài liệu xác thực giải thích biểu tượng con rùa vàng cho mẫu xe này. Quý khách vui lòng cho biết mẫu xe, đời xe hoặc gửi ảnh biểu tượng để đối chiếu đúng cảnh báo."
        understanding = state.get('turn_understanding') or {}
        goal = understanding.get('goal')
        if understanding.get('move') == 'verify_claim':
            reply = ('Em chưa có nguồn đủ để xác nhận số nào đúng cho xe đang hỏi. '
                     'Nếu câu trả lời trước đưa số chưa có nguồn thì em xin đính chính: số đó chưa được xác thực. '
                     'Cần đối chiếu phiên bản, đời xe và chuẩn đo trong nguồn; Quý khách cho biết phiên bản và đời xe nhé.')
        elif understanding.get('move') in {'elaborate', 'ask_status', 'ask_next_step'}:
            reasons = {
                'warranty': 'Thời hạn phụ thuộc hạng mục, đời xe, phương án pin và điều kiện sử dụng. Cần đối chiếu chính sách đúng xe; Quý khách cho biết đời xe và loại sử dụng nhé.',
                'range': 'Quãng đường phụ thuộc phiên bản, đời xe và chuẩn đo như WLTP/NEDC; thực tế còn phụ thuộc tốc độ, nhiệt độ và mức tiêu thụ. Quý khách cho biết phiên bản và đời xe để đối chiếu nhé.',
                'charging': 'Thời gian sạc phụ thuộc loại trụ/công suất, mức pin đầu–cuối và nhiệt độ pin. Quý khách cho biết trụ AC hay DC và công suất trụ nhé.',
                'capacity': 'Dung lượng cần đúng phiên bản và đời xe; dung lượng danh định khác dung lượng sử dụng được, SOC và SOH. Nếu chưa biết phiên bản, Quý khách có thể xem hồ sơ xe hoặc nhờ showroom kiểm tra.',
                'maintenance': 'Mốc bảo dưỡng cần đối chiếu sổ bảo dưỡng đúng đời xe và điều kiện sử dụng, không tự chọn một số km chung. Quý khách cho biết đời xe và số km hiện tại nhé.',
            }
            if goal in reasons:
                reply = 'Em chưa có nguồn đủ để xác nhận thông tin cụ thể. ' + reasons[goal]
        return {
            "is_no_source": True,
            "answer_status": 'error' if retrieval.get('status') in {'ERROR', 'UNAVAILABLE', 'TIMEOUT'} else 'needs_data',
            "retrieval_status": retrieval.get("status", "NO_SOURCE"),
            "retrieval_diagnostics": retrieval.get("diagnostics", {}),
            "rag_citations": [],
            "rag_context": [],
            "is_rag_query": True,
            "needs_staff_review": True,
            "rag_distance": retrieval.get("best_distance"),
            "response": reply,
            "final_response": reply,
            "guardrails": {**state.get("guardrails", {}), "low_confidence_escalated": True},
        }
    answer = candidate
    if color_snapshot and not generated:
        from src.services.vehicle_catalog import format_catalog_color_reply
        answer = format_catalog_color_reply(answer, citations)
    reply = f"Theo tài liệu VinFast:\n\n{answer}"
    if (state.get('turn_understanding') or {}).get('move') == 'verify_claim':
        reply += '\nCon số được đối chiếu với nguồn đang dẫn. Cần dùng đúng phiên bản, đời xe và điều kiện đo của nguồn, tránh so sánh các số theo chuẩn khác nhau.'
    if claim_check['conflicts']:
        reply += '\n\nSố liệu này khác câu trả lời trước. Cần đối chiếu điều kiện áp dụng trong nguồn; em đính chính theo nguồn đang dẫn và chưa xác nhận các điều kiện là tương đương.'
    return {
        "is_no_source": False,
        'answer_claims': [c.model_dump() for c in answer_claims],
        "retrieval_status": "SUCCESS",
        "answer_status": "answered",
        "retrieval_diagnostics": retrieval.get("diagnostics", {}),
        "is_rag_query": True,
        "rag_citations": citations,
        "rag_context": [c["relevant_snippet"] for c in citations],
        "rag_distance": min(c["distance"] for c in citations),
        "needs_staff_review": False,
        "response_type": "FAQ_ANSWER",
        "response": reply,
        "final_response": reply,
    }
