from functools import lru_cache
from threading import RLock

from src.config import get_settings

_client_lock = RLock()


@lru_cache(maxsize=4)
def _client(model: str, key: str, base_url: str, temperature: float, transport_timeout: float):
    # Sử dụng Google Gemini nếu model là gemini và key bắt đầu bằng AIza
    if "gemini" in model.lower() and key.startswith("AIza"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=key,
            temperature=temperature,
            max_retries=0,
            timeout=transport_timeout,
        )
    # Mặc định sử dụng OpenAI hoặc LiteLLM Gateway (openai/gpt-5.6, v.v.)
    from langchain_openai import ChatOpenAI
    kwargs = {
        "model": model,
        "temperature": temperature,
        "max_retries": 1,
        "timeout": transport_timeout,
    }
    if key:
        kwargs["api_key"] = key
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def get_llm():
    settings = get_settings()
    with _client_lock:
        key = settings.openai_api_key or settings.google_api_key
        base_url = settings.openai_base_url
        return _client(
            settings.model_name,
            key,
            base_url,
            settings.llm_temperature,
            max(10.0, settings.agent_llm_timeout_s),
        )
