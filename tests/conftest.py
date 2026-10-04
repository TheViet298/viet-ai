from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.config import get_settings
from src.main import app


@pytest.fixture(autouse=True)
def isolated_agent_environment(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "agent_llm_enabled", False)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setattr(settings, "chroma_persist_dir", str(tmp_path / "chroma"))


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm():
    """Mock LLM to avoid calling OpenAI during tests.

    Usage in test:
        def test_something(mock_llm):
            # LLM calls will return mock response instead of hitting OpenAI
            ...
    """
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
