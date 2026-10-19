"""SQL memory contracts: every request executes in a fresh Python process."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from src.models.db_models import User

pytest_plugins = ['tests.test_api.test_customer_chat_regressions']
ROOT = Path(__file__).resolve().parents[2]
SEED = 'Hãy nhớ xe của tôi là VF8 Plus, tôi ở Hà Nội'


def call(db, tmp_path, session, text, user='regression-customer', *, live=False, **payload):
    spec = {'database_url': str(db.bind.url), 'empty_index': str(tmp_path / 'empty-index'),
            'user_id': user, 'user_memory_enabled': True, 'live': live,
            'payload': {'session_id': session, 'message': text, **payload}}
    process = subprocess.run([sys.executable, str(ROOT / 'eval/cross_session_probe_worker.py')],
        input=json.dumps(spec), text=True, encoding='utf-8', capture_output=True, cwd=ROOT, timeout=50)
    assert process.returncode == 0, process.stderr[-2000:]
    return json.loads(process.stdout.strip().splitlines()[-1])


def message(row):
    assert row['status'] == 200, row
    return row['response']['data']['message']


@pytest.mark.parametrize('capability', [
    'same_session_restart', 'same_session_explicit_recall', 'same_session_recall_wording',
    'new_session_model', 'new_session_trim', 'new_session_city', 'latest_correction_new_session',
    'profile_model_new_session', 'other_user_isolation', 'fresh_incident_isolation', 'forget_old_session'])
def test_capabilities_in_new_process(customer_db, tmp_path, capability):
    rows = []
    if capability == 'profile_model_new_session':
        customer_db.get(User, 'regression-customer').vehicle_model = 'VF5'
        customer_db.commit()
        row = call(customer_db, tmp_path, 'profile', 'Xe tôi không sạc được')
        assert row['vehicle_context'].get('owned_model') == 'VF5'
        assert row['memory']['facts']['owned_vehicle.model']['source_kind'] == 'profile'
        rows.append(row)
    else:
        row = call(customer_db, tmp_path, 'a', 'Tư vấn VF8' if capability == 'fresh_incident_isolation' else SEED,
                   request_id='seed-request')
        message(row)
        rows.append(row)
        if capability == 'fresh_incident_isolation':
            row = call(customer_db, tmp_path, 'b', 'Xe tôi không sạc được')
            assert not row['memory']['facts']
            assert not row['vehicle_context'].get('incident_model')
            assert not row['context'].get('subject')
        elif capability == 'other_user_isolation':
            customer_db.add(User(id='user-b', username='user-b', password_hash='unused', role='CUSTOMER'))
            customer_db.commit()
            denied = call(customer_db, tmp_path, 'a', 'Xe tôi là dòng nào?', 'user-b')
            assert denied['status'] in (403, 404) and not denied['context']
            row = call(customer_db, tmp_path, 'b', 'Xe tôi là dòng nào?', 'user-b')
            assert not row['memory']['facts'] and 'VF8' not in message(row)
            rows.append(denied)
        else:
            assert row['memory']['revision'] == 1
            assert row['memory']['facts']['owned_vehicle.model']['value'] == 'VF8'
            assert row['memory']['facts']['owned_vehicle.version']['value'] == 'Plus'
            assert row['memory']['facts']['home_city']['value'] == 'Hà Nội'
            if capability == 'latest_correction_new_session':
                rows.append(call(customer_db, tmp_path, 'b', 'Không phải VF8, xe tôi là VF5, tôi ở Đà Nẵng'))
            if capability == 'forget_old_session':
                rows.append(call(customer_db, tmp_path, 'b', 'Hãy quên hết thông tin tôi đã nhờ lưu'))
                replay = call(customer_db, tmp_path, 'a', SEED, request_id='seed-request')
                assert replay['memory']['revision'] == 2 and 'VF8' not in message(replay)
                rows.append(replay)
            question = ('Thành phố tôi đã chọn ở cuộc trò chuyện trước là gì?' if capability == 'new_session_city' else
                        'Tôi đã chọn phiên bản nào ở cuộc trò chuyện trước?' if capability == 'new_session_trim' else
                        'Nhắc lại thông tin tôi đã khai báo trước đây.' if capability == 'latest_correction_new_session' else
                        'Xe tôi là dòng nào?')
            row = call(customer_db, tmp_path, 'a' if capability.startswith('same_session') or capability == 'forget_old_session' else 'c', question)
            answer = message(row)
            assert 'sự cố' not in answer and not row['response']['data']['vehicle_cards']
            if capability == 'forget_old_session':
                assert 'VF8' not in answer and all(f['value'] is None for f in row['memory']['facts'].values())
            elif capability == 'latest_correction_new_session':
                assert 'VF5' in answer and 'Đà Nẵng' in answer and 'VF8' not in answer
                assert row['memory']['facts']['owned_vehicle.version']['status'] == 'retracted'
            else:
                assert ('Hà Nội' if capability == 'new_session_city' else 'Plus' if capability == 'new_session_trim' else 'VF8') in answer
        rows.append(row)
    (tmp_path / 'cross-session-feature.json').write_text(json.dumps({'capability': capability,
        'process_per_request': True, 'turns': rows}, ensure_ascii=False, indent=2), encoding='utf-8')


@pytest.mark.asyncio
@pytest.mark.parametrize('length', [10, 20, 30])
async def test_two_users_interleaved_multitopic_chat(client, customer_db, monkeypatch, length):
    from src.config import get_settings
    from src.main import app
    from src.services.auth import get_optional_user, require_customer
    from src.models.db_models import ChatSession
    monkeypatch.setattr(get_settings(), 'user_memory_enabled', True)
    customer_db.add(User(id='second-user', username='second-user', password_hash='unused', role='CUSTOMER'))
    customer_db.commit()
    turns = [
        ('Xin chào', None), ('Tư vấn VF3', 'overview'),
        ('Ứng dụng VinFast có tính năng gì?', 'application'),
        ('Biểu phí sạc tại trạm sạc công cộng', 'charging_network'),
        ('Lịch bảo dưỡng định kỳ VF8 là gì?', 'maintenance'),
        ('Chính sách bảo hành pin VF8 bao lâu?', 'warranty'),
        ('Tôi muốn đăng ký lái thử VF5 ở Hà Nội', 'test_drive'),
        ('Tư vấn VF8', 'overview'),
        ('Nhắc lại thông tin tôi đã khai báo trước đây.', None),
        ('Cảm ơn', None),
    ]
    rows = []
    for number in range(length):
        for user_id, model, city in [('regression-customer', 'VF8', 'Hà Nội'), ('second-user', 'VF5', 'Đà Nẵng')]:
            user = customer_db.get(User, user_id)
            def principal():
                return user
            app.dependency_overrides[get_optional_user] = principal
            app.dependency_overrides[require_customer] = principal
            if number == 0:
                text, goal = f'Hãy nhớ xe của tôi là {model} Plus, tôi ở {city}', None
            else:
                text, goal = turns[number % 10]
            payload = {'session_id': f'interleaved-{user_id}', 'message': text, 'request_id': f'{user_id}-{number}'}
            response = await client.post('/api/v1/customer/chat', json=payload)
            assert response.status_code == 200, response.text
            data = response.json()['data']
            if number % 7 == 0:
                replay = await client.post('/api/v1/customer/chat', json=payload)
                assert replay.json() == response.json()
            current = (await client.get('/api/v1/customer/memory')).json()['data']
            assert current['revision'] == 1
            assert current['facts']['owned_vehicle.model']['value'] == model
            assert current['facts']['home_city']['value'] == city
            customer_db.expire_all()
            session = customer_db.get(ChatSession, payload['session_id'])
            context = session.memory_states[session.id]['conversation_context']
            assert session.owner == 'user:' + user_id
            if goal:
                assert context['active_goal'] == goal, (number, text, context)
            if number % 10 == 8:
                assert model in data['message'] and city in data['message']
            assert not data['show_emergency_banner']
            rows.append({'user': user_id, 'turn': number, 'goal': context.get('active_goal'), 'revision': current['revision']})
    assert len(rows) == length * 2


@pytest.mark.skipif(os.getenv('USER_MEMORY_LIVE') != '1', reason='Explicit provider configuration required')
def test_new_process_memory_with_live_configuration(customer_db, tmp_path):
    first = call(customer_db, tmp_path, 'live-a', SEED, live=True)
    assert first['memory']['revision'] == 1
    second = call(customer_db, tmp_path, 'live-b', 'What car and trim did I tell you I own, and which city do I live in?', live=True, language='vi')
    assert all(term in message(second) for term in ['VF8', 'Plus', 'Hanoi'])
    assert second['response']['data']['language'] == 'en'
    assert not second['context'].get('active_goal')
    (tmp_path / 'memory-live.json').write_text(json.dumps({'provider_configured': True,
        'process_per_request': True, 'model_generation_needed': False,
        'turns': [first, second]}, ensure_ascii=False, indent=2), encoding='utf-8')
