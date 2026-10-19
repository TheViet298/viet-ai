"""One synthetic HTTP request in a fresh process; providers disabled by default."""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['LANGFUSE_TRACING_ENABLED'] = 'false'


async def run(spec):
    from src.config import get_settings
    settings = get_settings()
    settings.agent_llm_enabled = False
    settings.database_url = spec['database_url']
    settings.chroma_persist_dir = spec['empty_index']
    if spec.get('live'):
        from src.config import Settings
        configured = Settings(_env_file=Path('D:/142.AI20K/P-142/.env'))
        for name in ('openai_api_key', 'openai_base_url', 'google_api_key', 'model_name', 'normalization_model'):
            setattr(settings, name, getattr(configured, name))
        settings.agent_llm_enabled = True
        settings.chroma_persist_dir = str(Path(__file__).resolve().parents[1] / '.test-runs/answer-gap-index')
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from httpx import ASGITransport, AsyncClient
    from src.main import app
    from src.db import get_db
    from src.models.db_models import ChatSession, User
    from src.services.auth import get_optional_user, require_customer

    engine = create_engine(spec['database_url'])
    with Session(engine) as db:
        user = db.get(User, spec['user_id'])
        assert user is not None
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_optional_user] = lambda: user
        app.dependency_overrides[require_customer] = lambda: user
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/api/v1/customer/chat', json=spec['payload'])
        db.expire_all()
        session = db.get(ChatSession, spec['payload']['session_id'])
        # Never disclose another principal's state to the probe caller.
        snapshot = (session.memory_states or {}).get(session.id, {}) if session and response.status_code == 200 else {}
        result = {'status': response.status_code, 'response': response.json(),
                  'context': snapshot.get('conversation_context', {}),
                  'vehicle_context': snapshot.get('vehicle_context', {}),
                  'persisted_profile_model': db.get(User, user.id).vehicle_model}
    engine.dispose()
    return result


if __name__ == '__main__':
    print(json.dumps(asyncio.run(run(json.load(sys.stdin))), ensure_ascii=True))
