from __future__ import annotations

import asyncio
import time

from pydantic import BaseModel, Field

from src.agents.context_manager import build_7_layer_context, load_prompt, resolve_policy_conflict, trim_context_layers
from src.agents.guardrails import sanitize_pii
from src.agents.state import AgentState
from src.agents.tools.vinfast_tools import vinfast_manual_search
from src.config import get_settings
from src.services.agent_llm import structured_call
from src.services.answer_evidence import AnswerClaim, extract_numeric_claims, is_turtle_question, validate_answer_claims
from src.services.observability import observation, update_observation
from src.services.rag_service import RAGService, select_supported_evidence, valid_citation


class GroundedAnswer(BaseModel):
    answer: str = Field(max_length=3000)
    source_ids: list[str]
    supported: bool
    claims: list[AnswerClaim] = Field(default_factory=list)


async def rag_node(state: AgentState) -> dict:
    query = state.get("resolved_query") or state.get("latest_user_message", "")
    unsupported = any(term in query.lower() for term in ("bí mật", "nội bộ", "tháng sau", "không công khai", "chưa công khai"))
    remaining = state.get("llm_budget", {}).get("deadline", time.monotonic() + get_settings().agent_turn_timeout_s) - time.monotonic()
    retrieval = RAGService.failure("NO_SOURCE", "unsupported_request") if unsupported else RAGService.failure("TIMEOUT", "deadline_exhausted")
    if not unsupported and remaining > 0:
        try:
            search_query = query + " chỉ báo giới hạn công suất" if is_turtle_question(query) else query
            with observation('retrieval', as_type='retriever', metadata={'layer': 'retrieval',
                    'timeout_s': min(remaining, get_settings().rag_retrieval_timeout_s),
                    'timeout_source': 'turn_deadline' if remaining <= get_settings().rag_retrieval_timeout_s else 'retrieval_limit'}) as span:
                retrieval = await asyncio.wait_for(vinfast_manual_search(search_query, vehicle_model=state.get("vehicle_model")),
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
    if (state.get('turn_understanding') or {}).get('goal') == 'appearance':
        color_snapshot = [c for c in citations if c.get('catalog_scope') == 'model_colors']
        if color_snapshot:
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
    reply = "Hiện chưa có tài liệu chính thức đã xác thực đủ để trả lời yêu cầu này. Tôi sẽ ghi nhận để chuyên viên kiểm tra."
    if "điều kiện" in query.casefold() and "bảo hành" in query.casefold():
        reply = "Anh/chị đang hỏi điều kiện bảo hành của xe vừa trao đổi. Hiện tôi chưa có đoạn tài liệu xác thực đủ để giải thích điều kiện này; tôi sẽ chuyển chuyên viên kiểm tra, tránh nhầm với điều kiện bảo hành pin hoặc từng hạng mục."
    if retrieval.get("status") in {"UNAVAILABLE", "ERROR", "TIMEOUT"}:
        reply = "Hệ thống tra cứu hiện chưa hoàn tất được yêu cầu. Tôi sẽ chuyển chuyên viên kiểm tra."
    elif retrieval.get("diagnostics", {}).get("category") == "context_budget_exceeded":
        reply = "Tài liệu cần thiết vượt giới hạn xử lý hiện tại. Tôi sẽ chuyển chuyên viên kiểm tra đầy đủ điều kiện."
    generated = None
    if citations and state.get("confidence_score", 0) >= 0.60:
        public_snapshot = bool(color_snapshot) or retrieval.get('diagnostics', {}).get('category') == 'verified_public_price_snapshot'
        generated = None if public_snapshot else await structured_call({**state, "rag_citations": citations}, "rag_qa", GroundedAnswer)
        if generated is None and get_settings().agent_llm_enabled and not public_snapshot:
            citations = []
            reply = "Tôi chưa hoàn tất được việc tạo câu trả lời từ tài liệu đã tìm thấy. Anh/chị vui lòng thử lại; tôi không thể xác nhận nội dung lúc này."
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
    claim_check = {'supported': True, 'conflicts': []}
    answer_claims = []
    if citations:
        candidate = generated.answer if generated else '\n\n'.join(c['relevant_snippet'] for c in citations)
        fact_context = (state.get('conversation_context') or {}).get('facts', {})
        version = (fact_context.get('version') or {}).get('value') or ''
        subject = f'{state.get("vehicle_model") or ""} {version}'.strip()
        if 'bảo hành' in query.casefold() and 'pin' in query.casefold():
            subject += ' ' + ((fact_context.get('component') or {}).get('value') or ('pin cao áp' if 'pin cao áp' in query.casefold() else 'pin'))
        answer_claims = [*(generated.claims if generated else []),
                         *extract_numeric_claims(candidate, citations, subject, query)]
        prior = [AnswerClaim.model_validate(c) for entry in (state.get('conversation_context') or {}).get('last_answer', [])
                 for c in entry.get('claims', [])]
        claim_check = validate_answer_claims(answer_claims, citations, prior)
        if not claim_check['supported']:
            citations = []
            reply = 'Em chưa có bằng chứng phù hợp để xác nhận số liệu cho đúng xe và điều kiện đang hỏi. Anh/chị cho biết phiên bản và đời xe để đối chiếu nhé.'
            retrieval = {**retrieval, 'status': 'NO_SOURCE', 'diagnostics': {
                **retrieval.get('diagnostics', {}), 'category': 'unsupported_numeric_claim', 'claim_check': claim_check}}
    if not citations:
        if retrieval.get("status") == "SUCCESS":
            retrieval = {**retrieval, "status": "NO_SOURCE", "diagnostics": {
                **retrieval.get("diagnostics", {}), "category": "missing_answer_evidence"}}
        if is_turtle_question(query) and retrieval.get("status") == "NO_SOURCE":
            reply = "Tôi chưa tìm được đoạn tài liệu xác thực giải thích biểu tượng con rùa vàng cho mẫu xe này. Anh/chị vui lòng cho biết mẫu xe, đời xe hoặc gửi ảnh biểu tượng để đối chiếu đúng cảnh báo."
        understanding = state.get('turn_understanding') or {}
        goal = understanding.get('goal')
        if understanding.get('move') == 'verify_claim':
            reply = ('Em chưa có nguồn đủ để xác nhận số nào đúng cho xe đang hỏi. '
                     'Nếu câu trả lời trước đưa số chưa có nguồn thì em xin đính chính: số đó chưa được xác thực. '
                     'Cần đối chiếu phiên bản, đời xe và chuẩn đo trong nguồn; anh/chị cho biết phiên bản và đời xe nhé.')
        elif understanding.get('move') in {'elaborate', 'ask_status', 'ask_next_step'}:
            reasons = {
                'warranty': 'Thời hạn phụ thuộc hạng mục, đời xe, phương án pin và điều kiện sử dụng. Cần đối chiếu chính sách đúng xe; anh/chị cho biết đời xe và loại sử dụng nhé.',
                'range': 'Quãng đường phụ thuộc phiên bản, đời xe và chuẩn đo như WLTP/NEDC; thực tế còn phụ thuộc tốc độ, nhiệt độ và mức tiêu thụ. Anh/chị cho biết phiên bản và đời xe để đối chiếu nhé.',
                'charging': 'Thời gian sạc phụ thuộc loại trụ/công suất, mức pin đầu–cuối và nhiệt độ pin. Anh/chị cho biết trụ AC hay DC và công suất trụ nhé.',
                'capacity': 'Dung lượng cần đúng phiên bản và đời xe; dung lượng danh định khác dung lượng sử dụng được, SOC và SOH. Nếu chưa biết phiên bản, anh/chị có thể xem hồ sơ xe hoặc nhờ showroom kiểm tra.',
                'maintenance': 'Mốc bảo dưỡng cần đối chiếu sổ bảo dưỡng đúng đời xe và điều kiện sử dụng, không tự chọn một số km chung. Anh/chị cho biết đời xe và số km hiện tại nhé.',
            }
            if goal in reasons:
                reply = 'Em chưa có nguồn đủ để xác nhận thông tin cụ thể. ' + reasons[goal]
        return {
            "is_no_source": True,
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
    if generated:
        citations = [c for c in citations if c["source_id"] in generated.source_ids]
    for citation in citations:
        citation["relevant_snippet"] = sanitize_pii(citation["relevant_snippet"])[0]
    answer = sanitize_pii(generated.answer if generated else "\n\n".join(c["relevant_snippet"] for c in citations))[0]
    reply = f"Theo tài liệu VinFast:\n\n{answer}"
    if (state.get('turn_understanding') or {}).get('move') == 'verify_claim':
        reply += '\nCon số được đối chiếu với nguồn đang dẫn. Cần dùng đúng phiên bản, đời xe và điều kiện đo của nguồn, tránh so sánh các số theo chuẩn khác nhau.'
    if claim_check['conflicts']:
        reply += '\n\nSố liệu này khác câu trả lời trước. Cần đối chiếu điều kiện áp dụng trong nguồn; em đính chính theo nguồn đang dẫn và chưa xác nhận các điều kiện là tương đương.'
    return {
        "is_no_source": False,
        'answer_claims': [c.model_dump() for c in answer_claims],
        "retrieval_status": "SUCCESS",
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
