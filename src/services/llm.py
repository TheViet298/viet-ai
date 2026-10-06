from functools import lru_cache
from threading import RLock

from langchain_google_genai import ChatGoogleGenerativeAI

from src.config import get_settings

_client_lock = RLock()


@lru_cache(maxsize=4)
def _client(model: str, key: str, temperature: float, transport_timeout: float) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=key,
        temperature=temperature,
        max_retries=0,
        # Provider rejects transport deadlines below ten seconds. The caller's
        # asyncio deadline still enforces the configured foreground budget.
        timeout=transport_timeout,
    )


def get_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    with _client_lock:
        return _client(settings.model_name, settings.google_api_key, settings.llm_temperature, max(10.0, settings.agent_llm_timeout_s))
