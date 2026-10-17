from src.services.conversation_context import ConversationContext, ConversationFact
from src.services.conversation_progress import derive_progress


def test_booking_requires_external_action_and_real_receipt():
    context = ConversationContext(active_goal='test_drive')
    progress = derive_progress(context, {}, None, None)
    assert progress.state == 'external_action_required'
    assert progress.action_receipt is None
    assert derive_progress(context, {}, None, {'id': 'booking-123', 'goal': 'test_drive', 'status': 'completed'}).state == 'action_completed'


def test_unknown_version_is_not_required_again():
    context = ConversationContext(active_goal='quote', subject='VF8',
                                  facts={'version': ConversationFact(source_turn=1, status='unknown')})
    assert 'version' not in derive_progress(context, {}, None, None).missing_fields


def test_case_status_comes_from_snapshot_not_prose():
    context = ConversationContext(active_goal='incident')
    progress = derive_progress(context, {}, {'id': 'CASE-1', 'status': 'Staff Reviewing', 'facts': {'soc': '35%', 'error_code': 'CC01'}}, None)
    assert progress.case_id == 'CASE-1'
    assert progress.state != 'action_completed'
    assert progress.missing_fields == ['station_location', 'charger_id']


def test_vietnamese_incident_reply_uses_customer_status_label():
    from src.services.conversation_context import TurnUnderstanding
    from src.services.conversation_progress import progress_reply
    context = ConversationContext(active_goal='incident')
    snapshot = {'id': 'CASE-1', 'status': 'Staff Reviewing'}
    progress = derive_progress(context, {}, snapshot, None)
    reply = progress_reply(TurnUnderstanding(move='ask_status', original_text='Trạng thái hồ sơ?',
        resolved_query='Trạng thái hồ sơ?'), context, progress, snapshot)
    assert 'Đang chờ nhân viên xem xét' in reply
    assert 'Staff Reviewing' not in reply
