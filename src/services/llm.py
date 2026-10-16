from functools import lru_cache
from threading import RLock

from src.config import get_settings

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

_client_lock = RLock()


@lru_cache(maxsize=4)
def _client(model: str, key: str, base_url: str, temperature: float, transport_timeout: float,
            normalization: bool = False):
    # Sử dụng Google Gemini nếu model là gemini và key bắt đầu bằng AIza
    if "gemini" in model.lower() and key.startswith("AIza"):
        if ChatGoogleGenerativeAI is None:
            raise ImportError(
                "Thư viện langchain-google-genai chưa được cài đặt. "
                "Cài đặt bằng lệnh: pip install langchain-google-genai"
            )
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=key,
            temperature=temperature,
            max_retries=0,
            timeout=transport_timeout,
            **({'thinking_budget': 0, 'max_output_tokens': 256} if normalization else {}),
        )

    # Mặc định sử dụng OpenAI hoặc LiteLLM Gateway (openai/gpt-5.6, v.v.)
    if ChatOpenAI is None:
        raise ImportError(
            "Thư viện langchain-openai chưa được cài đặt. "
            "Cài đặt bằng lệnh: pip install langchain-openai"
        )
    # Các dòng mô hình reasoning / gpt-5 / o1 trên LiteLLM Gateway chỉ chấp nhận temperature=1.0 mặc định
    effective_temp = 1.0 if any(m in model.lower() for m in ["gpt-5", "o1", "o3"]) else temperature
    kwargs = {
        "model": model,
        "temperature": effective_temp,
        "max_retries": 0,
        "timeout": transport_timeout,
    }
    if key:
        kwargs["api_key"] = key
    if base_url:
        kwargs["base_url"] = base_url
    if normalization:
        kwargs['max_tokens'] = 256
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


def get_normalization_llm():
    settings = get_settings()
    direct_google = 'gemini' in settings.normalization_model.lower() and settings.google_api_key.startswith('AIza')
    if 'gemini' in settings.normalization_model.lower() and not direct_google and not (
            settings.openai_api_key and settings.openai_base_url):
        raise ValueError('Configure GOOGLE_API_KEY or an OpenAI-compatible Gemini gateway for NORMALIZATION_MODEL')
    with _client_lock:
        return _client(settings.normalization_model,
                       settings.google_api_key if direct_google else settings.openai_api_key,
                       '' if direct_google else settings.openai_base_url, 0,
                       max(10.0, settings.normalization_timeout_s), normalization=True)
