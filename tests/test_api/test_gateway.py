import os

from openai import OpenAI
import pytest

from src.config import get_settings


def check_gateway_connection() -> str:
    """Kiểm tra kết nối tới LLM Gateway."""
    settings = get_settings()
    client = OpenAI(
        api_key=settings.openai_api_key or os.getenv("OPENAI_API_KEY", "dummy"),
        base_url=settings.openai_base_url or os.getenv("OPENAI_BASE_URL", "https://litellm.vlearn.dev/v1"),
    )
    model = os.getenv("MODEL", settings.model_name or "gpt-4o-mini")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Reply with exactly: PONG"},
        ],
        max_tokens=256,
    )
    return response.choices[0].message.content or ""


@pytest.mark.integration
def test_api_gateway_live():
    """Test case cho pytest (bỏ qua nếu không có API key trong môi trường test/CI)."""
    settings = get_settings()
    if not settings.openai_api_key and not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Bỏ qua test gateway do chưa cấu hình OPENAI_API_KEY")

    reply = check_gateway_connection()
    assert "PONG" in reply.upper()


if __name__ == "__main__":
    print("Testing API Gateway connection...")
    try:
        res = check_gateway_connection()
        print("Success! Response from Gateway:", res)
    except Exception as e:
        print("Failed to connect to Gateway:", str(e))
