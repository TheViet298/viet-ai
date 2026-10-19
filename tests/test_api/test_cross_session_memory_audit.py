"""Capability probes: missing cross-session recall deliberately fails its contract."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.models.db_models import User

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']
pytestmark = pytest.mark.skipif(os.getenv('ANSWER_GAP_AUDIT') != '1', reason='Explicit cross-session capability audit only')
ROOT = Path(__file__).resolve().parents[2]


def call_worker(db, tmp_path, session, message, user='regression-customer', live=False):
    spec = {'database_url': str(db.bind.url), 'empty_index': str(tmp_path / 'empty-index'), 'user_id': user,
            'payload': {'session_id': session, 'message': message}, 'live': live}
    process = subprocess.run([sys.executable, str(ROOT / 'eval/cross_session_probe_worker.py')],
                             input=json.dumps(spec), text=True, encoding='utf-8', capture_output=True,
                             cwd=ROOT, timeout=50)
    assert process.returncode == 0, process.stderr[-2500:]
    return json.loads(process.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize('capability', ['same_session_restart', 'same_session_explicit_recall', 'same_session_recall_wording', 'new_session_model', 'new_session_trim',
                                     'new_session_city', 'latest_correction_new_session',
                                     'profile_model_new_session', 'other_user_isolation', 'fresh_incident_isolation'])
def test_cross_session_capability(customer_db, tmp_path, capability):
    rows = []
    if capability == 'profile_model_new_session':
        customer_db.get(User, 'regression-customer').vehicle_model = 'VF5'
        customer_db.commit()
        result = call_worker(customer_db, tmp_path, 'profile-new', 'Xe tôi không sạc được')
        rows.append(result)
        supported = result['vehicle_context'].get('owned_model') == 'VF5'
    else:
        seed = ('Tư vấn VF8' if capability == 'fresh_incident_isolation' else
                'Giá lăn bánh VF8 Plus ở Hà Nội?' if capability == 'same_session_restart' else
                'Hãy nhớ xe của tôi là VF8 Plus, tôi ở Hà Nội')
        first = call_worker(customer_db, tmp_path, 'memory-a', seed)
        assert first['status'] == 200
        rows.append(first)
        if capability != 'fresh_incident_isolation':
            assert first['context']['subject'] == 'VF8'
            assert first['context']['facts']['version']['value'] == 'Plus'
            assert first['context']['facts']['city']['value'] == 'Hà Nội'
        if capability == 'latest_correction_new_session':
            rows.append(call_worker(customer_db, tmp_path, 'memory-a',
                                    'Không phải VF8, xe tôi là VF5, tôi ở Đà Nẵng'))
            assert rows[-1]['context']['subject'] == 'VF5'
            assert rows[-1]['context']['facts']['city']['value'] == 'Đà Nẵng'
        if capability == 'other_user_isolation':
            customer_db.add(User(id='probe-user-b', username='probe-b', password_hash='unused', role='CUSTOMER'))
            customer_db.commit()
            denied = call_worker(customer_db, tmp_path, 'memory-a', 'Tôi đã dùng xe gì?', 'probe-user-b')
            fresh = call_worker(customer_db, tmp_path, 'memory-b', 'Tôi dùng xe gì?', 'probe-user-b')
            rows.extend([denied, fresh])
            supported = denied['status'] == 403 and not fresh['context'].get('subject')
        else:
            same = capability in {'same_session_restart', 'same_session_explicit_recall', 'same_session_recall_wording'}
            prompt = ('Xe tôi không sạc được' if capability == 'fresh_incident_isolation' else
                      'Tôi đã nói rồi, còn thiếu gì?' if capability == 'same_session_restart' else
                      'Xe tôi là dòng nào?' if capability in {'same_session_explicit_recall', 'same_session_recall_wording'} else
                      'Xe tôi là dòng nào?' if capability == 'new_session_model' else
                      'Tôi đã chọn phiên bản nào ở cuộc trò chuyện trước?' if capability == 'new_session_trim' else
                      'Thành phố tôi đã chọn ở cuộc trò chuyện trước là gì?' if capability == 'new_session_city' else
                      'Nhắc lại thông tin tôi đã khai báo ở cuộc trò chuyện trước.')
            result = call_worker(customer_db, tmp_path, 'memory-a' if same else 'memory-b', prompt)
            rows.append(result)
            assert result['status'] == 200
            ctx, facts = result['context'], result['context'].get('facts', {})
            if capability == 'same_session_restart':
                supported = (ctx.get('subject') == 'VF8' and facts.get('version', {}).get('value') == 'Plus'
                             and facts.get('city', {}).get('value') == 'Hà Nội')
            elif capability == 'same_session_explicit_recall':
                supported = 'VF8' in result['response']['data']['message']
            elif capability == 'same_session_recall_wording':
                supported = 'sự cố' not in result['response']['data']['message']
            elif capability == 'new_session_model':
                supported = ctx.get('subject') == 'VF8'
            elif capability == 'new_session_trim':
                supported = facts.get('version', {}).get('value') == 'Plus'
            elif capability == 'new_session_city':
                supported = facts.get('city', {}).get('value') == 'Hà Nội'
            elif capability == 'latest_correction_new_session':
                supported = ctx.get('subject') == 'VF5' and facts.get('city', {}).get('value') == 'Đà Nẵng'
            else:
                supported = not result['vehicle_context'].get('incident_model') and not ctx.get('subject')
    (tmp_path / 'cross-session.json').write_text(json.dumps({'capability': capability,
        'process_per_request': True, 'supported': supported, 'turns': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    assert supported, f'{capability}: capability not supported; see cross-session.json'


@pytest.mark.skipif(os.getenv('ANSWER_GAP_LIVE') != '1', reason='Explicit configured-provider test only')
def test_cross_session_with_configured_provider(customer_db, tmp_path):
    first = call_worker(customer_db, tmp_path, 'live-memory-a',
                        'Hãy nhớ xe của tôi là VF8 Plus, tôi ở Hà Nội', live=True)
    assert first['status'] == 200
    assert first['context']['subject'] == 'VF8'
    second = call_worker(customer_db, tmp_path, 'live-memory-b',
                         'Xe của tôi là dòng nào, phiên bản nào? Tôi ở đâu?', live=True)
    supported = second['status'] == 200 and second['context'].get('subject') == 'VF8'
    (tmp_path / 'cross-session.json').write_text(json.dumps({'capability': 'new_session_configured_provider',
        'process_per_request': True, 'supported': supported, 'turns': [first, second]}, ensure_ascii=False, indent=2), encoding='utf-8')
    assert supported, 'New-session recall unavailable even with configured provider'
