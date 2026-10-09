"""Ten validation requests and evidence-based verdicts (no provider mocks here)."""


def matrix_cases() -> list[dict]:
    return [
        {'case_id': 'LF-01', 'kind': 'chat', 'message': 'Xin chào, bạn có thể giúp tôi tìm hiểu cách sử dụng xe VinFast không?'},
        {'case_id': 'LF-02', 'kind': 'chat', 'message': 'Phạm vi bảo hành xe ô tô VinFast gồm những gì?', 'vehicle_model': 'VF8'},
        {'case_id': 'LF-03', 'kind': 'chat', 'message': 'Chính sách bảo hành bí mật chưa công khai của VinFast tháng sau là gì?'},
        {'case_id': 'LF-04', 'kind': 'chat', 'message': 'Xin chào, xe của tôi là VF8.', 'session_group': 'memory', 'vehicle_model': 'VF8'},
        {'case_id': 'LF-05', 'kind': 'chat', 'message': 'Cảm ơn, tôi muốn trao đổi tiếp về chiếc xe này.', 'session_group': 'memory'},
        {'case_id': 'LF-06', 'kind': 'upload', 'image_kind': 'exterior'},
        {'case_id': 'LF-07', 'kind': 'upload', 'image_kind': 'dashboard'},
        {'case_id': 'LF-08', 'kind': 'chat', 'message': 'Xe đang bốc khói và có mùi khét!'},
        {'case_id': 'LF-09', 'kind': 'chat', 'message': 'Tôi cần trao đổi thêm, bạn có thể giúp tôi tìm hiểu xe VinFast không?', 'fault_injected': True},
        {'case_id': 'LF-10', 'kind': 'chat', 'message': 'Xin chào, hãy hướng dẫn tôi làm quen với xe điện VinFast.'},
    ]


def evaluate_case(case_id: str, http_status: int, response: dict, observations: list[dict]) -> dict:
    reasons = []
    roots = [o for o in observations if o.get('isRootObservation') or
             (o.get('name', '').startswith('p142.') and not o.get('parentObservationId'))]
    if not observations or not roots:
        return {'status': 'BLOCKED', 'reasons': ['cloud_root_not_found']}
    if len(roots) != 1:
        return {'status': 'FAIL', 'reasons': ['root_count_is_not_one']}
    if http_status != 200:
        return {'status': 'FAIL', 'reasons': [f'http_{http_status}']}
    data = response.get('data', response)
    generations = [o for o in observations if o.get('type') == 'GENERATION']
    successful = [o for o in generations if o.get('level') != 'ERROR' and o.get('endTime')]
    if case_id in {'LF-01', 'LF-02', 'LF-06', 'LF-07', 'LF-10'} and not successful:
        return {'status': 'BLOCKED', 'reasons': ['successful_live_generation_missing']}
    if case_id == 'LF-02' and not data.get('citations'):
        reasons.append('rag_supported_citation_missing')
    if case_id == 'LF-03' and (not data.get('is_no_source') or data.get('citations')):
        reasons.append('no_source_contract_failed')
    if case_id == 'LF-05' and (data.get('_session_turn', 0) < 2 or data.get('_vehicle_model') != 'VF8'):
        reasons.append('session_memory_not_preserved')
    if case_id in {'LF-06', 'LF-07'}:
        signals = data.get('detected_signals', {})
        if signals.get('analysis_error'):
            return {'status': 'BLOCKED', 'reasons': [signals['analysis_error']]}
        if data.get('analysis_status') != 'ANALYZED':
            reasons.append('upload_not_analyzed')
    if case_id == 'LF-08' and (not data.get('is_safety_trigger') or data.get('priority') != 'CRITICAL'):
        reasons.append('emergency_contract_failed')
    if case_id == 'LF-09' and not any(
        o.get('statusMessage') == 'timeout' or o.get('metadata', {}).get('outcome') == 'timeout'
        for o in observations
    ):
        reasons.append('injected_timeout_not_observed')
    if case_id == 'LF-10' and not roots[0].get('endTime'):
        reasons.append('shutdown_root_not_finished')
    return {'status': 'FAIL' if reasons else 'PASS', 'reasons': reasons}
