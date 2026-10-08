from functools import lru_cache
from threading import RLock

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.config import get_settings

_client_lock = RLock()


@lru_cache(maxsize=4)
def _client(model: str, google_key: str, openai_key: str, base_url: str, temperature: float, transport_timeout: float):
    if "gemini" in model.lower() and google_key and not openai_key:
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=google_key,
            temperature=temperature,
            max_retries=0,
            # Provider rejects transport deadlines below ten seconds. The caller's
            # asyncio deadline still enforces the configured foreground budget.
            timeout=transport_timeout,
        )
    kwargs = {
        "model": model,
        "temperature": temperature,
        "max_retries": 1,
        "timeout": transport_timeout,
    }
    if openai_key:
        kwargs["api_key"] = openai_key
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def get_llm():
    settings = get_settings()
    with _client_lock:
        return _client(
            settings.model_name,
            settings.google_api_key,
            settings.openai_api_key,
            settings.openai_base_url,
            settings.llm_temperature,
            max(10.0, settings.agent_llm_timeout_s),
        )
