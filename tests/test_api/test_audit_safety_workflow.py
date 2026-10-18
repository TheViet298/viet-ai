import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db import Base, get_db
from src.main import app
from src.models.db_models import Message, User
from src.services.auth import get_optional_user, require_customer


@pytest.fixture
def safety_account(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "audit-safety.db"}')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(id='audit-safety', username='audit-safety', password_hash='unused', role='CUSTOMER')
        db.add(user)
        db.commit()
        app.dependency_overrides.update({get_db: lambda: db, get_optional_user: lambda: user,
                                         require_customer: lambda: user})
        yield db
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize('message', [
    'The accelerator pedal on my VF8 is stuck while I am driving.',
    'A tire on my VF8 has just burst on the highway.',
    'My VF7 brakes have stopped working while I am driving.',
    'The brake pedal in my VF8 goes all the way to the floor while I am driving.',
    'Chân phanh VF8 của tôi sát sàn khi đang lái xe.',
])
async def test_natural_emergency_survives_exhausted_guest_quota(client, safety_account, message):
    app.dependency_overrides[get_optional_user] = lambda: None
    safety_account.add_all([Message(id=f'old-{i}', session_id='exhausted', sender_type='CUSTOMER', content='old')
                            for i in range(5)])
    safety_account.commit()
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'exhausted', 'message': message})
    assert response.status_code == 200
    data = response.json()['data']
    assert data['priority'] == 'CRITICAL' and data['show_emergency_banner']
    assert data['case_id'] is None
    assert data['safe_guidance']


@pytest.mark.asyncio
@pytest.mark.parametrize('message', [
    'My VF8 is not emitting smoke. I only want to ask about its price.',
    'There are no flames at the charging port of my VF7. I only want its price.',
])
async def test_english_denial_does_not_persist_an_emergency(client, safety_account, message):
    response = await client.post('/api/v1/customer/chat', json={'session_id': 'denied', 'message': message})
    assert response.status_code == 200
    data = response.json()['data']
    assert not data['show_emergency_banner'] and data['priority'] != 'CRITICAL'
    assert data['case_id'] is None
