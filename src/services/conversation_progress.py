"""Business progress derives from server capabilities and authorized records."""
from typing import Literal

from pydantic import BaseModel, Field

from src.services.conversation_context import ConversationContext, TurnUnderstanding, normalized


CASE_STATUS_VI = {
    'New': 'Mới tiếp nhận', 'Needs Information': 'Cần bổ sung thông tin',
    'Staff Reviewing': 'Đang chờ nhân viên xem xét', 'In Progress': 'Đang xử lý',
    'Resolved': 'Đã giải quyết', 'Closed': 'Đã đóng', 'Reopened': 'Đã mở lại',
}


class ConversationProgress(BaseModel):
    state: Literal['collecting_input', 'ready_to_lookup', 'needs_verified_data',
                   'external_action_required', 'action_pending', 'action_completed', 'cancelled_intent']
    known_facts: dict[str, str] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    next_action: str = ''
    case_id: str | None = None
    action_receipt: dict | None = None


def derive_progress(context: ConversationContext, capabilities: dict[str, bool],
                    case_snapshot: dict | None, action_receipt: dict | None) -> ConversationProgress:
    known = {k: v.value for k, v in context.facts.items() if v.status == 'confirmed' and v.value is not None}
    supplied = {key for key, fact in context.facts.items() if fact.status != 'retracted'}
    if context.subject:
        known['model'] = context.subject
    result = ConversationProgress(state='ready_to_lookup', known_facts=known)
    if context.action.get('state') == 'cancelled_intent':
        result.state, result.next_action = 'cancelled_intent', 'Dừng thu thập cho ý định này; lịch bên ngoài cần hủy tại nơi đã đặt.'
        return result
    if action_receipt and action_receipt.get('id') and action_receipt.get('goal') == context.active_goal:
        result.action_receipt = action_receipt
        result.state = 'action_completed' if action_receipt.get('status') == 'completed' else 'action_pending'
        return result
    is_booking = context.active_goal == 'test_drive' or context.active_goal == 'maintenance' and any(
        term in normalized(context.topic) for term in ('dat lich', 'dat hen', 'muon bao duong'))
    if is_booking:
        capability = 'book_test_drive' if context.active_goal == 'test_drive' else 'book_maintenance'
        result.state = 'collecting_input' if capabilities.get(capability, False) else 'external_action_required'
        result.blocked_reason = 'Chat chưa có kết nối xác nhận lịch trống và đặt lịch.'
        result.next_action = 'Đăng ký trên Ứng dụng VinFast hoặc liên hệ showroom/xưởng để xác nhận lịch.'
        result.missing_fields = [k for k in ('city', 'date') if k not in supplied]
        if known.get('date') in {'thu bay', 'chu nhat', 'ngay mai', 'hom nay'}:
            result.missing_fields = list(dict.fromkeys([*result.missing_fields, 'exact_date']))
    elif context.active_goal == 'quote':
        result.state = 'needs_verified_data'
        result.next_action = 'Tra giá bán công bố đúng phiên bản, sau đó chọn cấu hình trên công cụ tính lăn bánh.'
        result.missing_fields = [k for k in ('version',) if k not in supplied]
    elif context.active_goal == 'incident':
        snapshot = case_snapshot or {}
        result.case_id = snapshot.get('id')
        result.known_facts.update({k: str(v) for k, v in snapshot.get('facts', {}).items() if v})
        result.state = 'action_pending' if result.case_id else 'collecting_input'
        required = ('station_location', 'charger_id') if result.known_facts.get('error_code') else ('location', 'symptom')
        result.missing_fields = [k for k in required if not result.known_facts.get(k)]
        result.next_action = 'Bổ sung thông tin còn thiếu để chuyên viên kiểm tra hồ sơ.'
    elif context.active_goal in {'warranty', 'range', 'capacity', 'charging', 'maintenance'}:
        result.missing_fields = [k for k in ('version', 'year') if k not in supplied]
    result.missing_fields = result.missing_fields[:2]
    return result


def build_reply_constraints(turn: TurnUnderstanding, context: ConversationContext, progress: ConversationProgress) -> dict:
    return {'known_facts': progress.known_facts, 'ask_only': progress.missing_fields[:2],
            'may_claim_completed': progress.state == 'action_completed' and bool(progress.action_receipt),
            'blocked_reason': progress.blocked_reason, 'next_action': progress.next_action,
            'original_text': turn.original_text, 'goal': context.active_goal}


def progress_reply(turn: TurnUnderstanding, context: ConversationContext, progress: ConversationProgress,
                   case_snapshot: dict | None = None) -> str | None:
    """Deterministic fallback for operational status; no RAG-invented actions."""
    if not context.active_goal or turn.move == 'new_incident':
        return None
    if turn.needs_confirmation:
        goal_label = {'quote': 'giá xe và dự toán lăn bánh', 'warranty': 'bảo hành',
                      'test_drive': 'lái thử', 'maintenance': 'bảo dưỡng', 'range': 'quãng đường',
                      'capacity': 'dung lượng pin', 'charging': 'sạc pin', 'incident': 'sự cố xe',
                      'concept': 'khái niệm vừa trao đổi'}.get(context.active_goal, context.active_goal)
        return f'Em vẫn đang hỗ trợ {goal_label}' + (f' của {context.subject}' if context.subject else '') + '. Anh/chị muốn em giải thích thêm phần nào, hay hướng dẫn bước tiếp theo?'
    facts = progress.known_facts
    summary = ', '.join(facts[k] for k in ('model', 'version', 'battery', 'city', 'area', 'date', 'time_window', 'component') if k in facts)
    if progress.state == 'cancelled_intent':
        if turn.move == 'ask_status':
            return 'Trong chat này em chưa đặt lịch hay tạo hồ sơ đặt hẹn cho Quý khách. Ý định đặt hẹn đã dừng; nếu có lịch đặt riêng ngoài chat, Quý khách cần kiểm tra tại nơi đã đặt.'
        return 'Em đã dừng yêu cầu này trong cuộc trò chuyện. Nếu Quý khách đã đặt lịch ở showroom hoặc ứng dụng, cần hủy tại nơi đã đặt; em chưa thực hiện hủy lịch bên ngoài.'
    if progress.state == 'external_action_required' and turn.move in {
        'request_action', 'ask_next_step', 'ask_status', 'supply_info', 'elaborate', 'correct',
    }:
        service = ('lái thử' if context.active_goal == 'test_drive' else
                   'sửa chữa' if any(term in normalized(context.topic) for term in ('sua xe', 'sua chua')) else 'bảo dưỡng')
        place = 'showroom' if context.active_goal == 'test_drive' else 'xưởng dịch vụ'
        opening = {
            'request_action': f'Hiện em chưa thể đặt lịch {service} trực tiếp trong chat. ',
            'ask_status': f'Em chưa có xác nhận lịch {service} đã được đặt. ',
            'ask_next_step': f'Bước tiếp theo là đăng ký {service} tại ứng dụng hoặc {place}. ',
            'elaborate': f'Lịch {service} cụ thể cần {place} xác nhận khung giờ còn trống; chat chưa có dữ liệu đó. ',
        }.get(turn.move, f'Em đã ghi nhận nhu cầu {service}. ')
        reply = opening + (f'Thông tin đang có: {summary}. ' if summary else '')
        reply += f'Quý khách có thể đăng ký qua Ứng dụng VinFast hoặc liên hệ {place} để xác nhận giờ hẹn.'
        if 'exact_date' in progress.missing_fields:
            reply += ' Quý khách muốn hẹn vào ngày, tháng, năm cụ thể nào? Em đã ghi nhận mốc thời gian tương đối ở trên; nơi đặt lịch cần xác nhận ngày hẹn chính xác.'
        elif progress.missing_fields:
            labels = {'city': 'khu vực thuận tiện', 'date': 'ngày mong muốn'}
            reply += ' Để hướng dẫn tiếp, Quý khách cho em biết ' + ' và '.join(labels[k] for k in progress.missing_fields) + ' nhé.'
        return reply
    if context.active_goal == 'capacity' and any(v.status == 'unknown' for k, v in context.facts.items() if k == 'version'):
        if 'tu van tiep' in normalized(turn.original_text):
            return ('Có thể tư vấn tiếp về dung lượng pin ' + (context.subject or 'xe đang hỏi') + '. '
                    'kWh là đơn vị năng lượng pin lưu trữ; dung lượng danh định là mức công bố, '
                    'còn dung lượng sử dụng được là phần hệ thống cho phép khai thác. '
                    'SOC cho biết mức nạp hiện tại, SOH phản ánh sức khỏe pin. '
                    'Đây là giải thích chung; khi xác định được phiên bản và đời xe, em mới đối chiếu con số riêng của xe.')
        return ('Em vẫn đang hỗ trợ dung lượng pin ' + (context.subject or 'xe đang hỏi') + '; Quý khách chưa xác định phiên bản. '
                'Có thể tư vấn tiếp về kWh, dung lượng danh định và dung lượng sử dụng được, nhưng chưa chốt thông số riêng của xe. '
                'Quý khách có thể xem tên phiên bản trong giấy tờ/hồ sơ xe hoặc nhờ showroom kiểm tra, rồi quay lại đối chiếu thông số.')
    if context.active_goal == 'warranty' and turn.move == 'supply_info' and 'doi xe' in normalized(turn.original_text):
        return ('Em đang đối chiếu bảo hành ' + (context.subject or 'xe đang hỏi') + '. '
                'Đời xe có thể cần để chọn đúng chính sách; Quý khách cho biết năm sản xuất hoặc xem trong hồ sơ xe nhé. Chưa đủ nguồn để xác nhận quyền lợi riêng của xe.')
    if context.active_goal == 'incident' and (turn.move in {'ask_status', 'ask_next_step'}
                                              or facts.get('reported_condition') and turn.move != 'new_question'):
        status_label = CASE_STATUS_VI.get((case_snapshot or {}).get('status'), 'chưa xác nhận')
        reply = (f'Hồ sơ {progress.case_id} hiện có trạng thái {status_label}. '
                 if progress.case_id else 'Em chưa có xác nhận hồ sơ hỗ trợ đã được tạo. ')
        if summary:
            reply += f'Thông tin đã ghi nhận: {summary}. '
        for key, label in [('soc', 'mức pin'), ('error_code', 'mã lỗi')]:
            if facts.get(key):
                reply += f'{label}: {facts[key]}. '
        if facts.get('reported_condition'):
            reply += 'Em ghi nhận Quý khách báo cảnh báo đã hết/an toàn; thông tin này chưa xác nhận xe đủ an toàn để tiếp tục chạy. '
            if 'di tiep' in normalized(turn.original_text):
                return reply + 'Quý khách nên liên hệ chuyên viên để kiểm tra trước khi tiếp tục hành trình. Nếu cảnh báo trở lại hoặc xe vẫn chạy yếu/bất thường, tiếp tục giữ xe ở vị trí an toàn và gọi hỗ trợ.'
        if progress.missing_fields:
            labels = {'station_location': 'vị trí trạm sạc', 'charger_id': 'mã trụ sạc', 'location': 'vị trí xe', 'symptom': 'triệu chứng hiện tại'}
            reply += 'Còn cần ' + ' và '.join(labels[k] for k in progress.missing_fields) + '. '
        return reply + 'Cần chuyên viên kiểm tra tình trạng vận hành; chưa có xác nhận kỹ thuật viên tiếp nhận hoặc cứu hộ đã xuất phát.'
    if turn.move == 'correct' and context.active_goal == 'warranty':
        reply = 'Em hiểu Quý khách đang hỏi bảo hành ' + facts.get('component', 'hạng mục vừa đính chính') + (f' của {context.subject}' if context.subject else '') + '. '
        return reply + 'Cần đối chiếu chính sách đúng đời xe và phương án pin; em chưa có nguồn đủ để chốt thời hạn. ' + (
            'Quý khách cho biết đời xe và pin mua kèm xe hay thay thế riêng nhé.' if 'battery' not in facts else 'Quý khách cho biết đời xe để đối chiếu nhé.')
    return None
