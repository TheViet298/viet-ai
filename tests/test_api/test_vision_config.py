from src.config import Settings


def test_vision_config_defaults_and_cardd_flag():
    settings = Settings()
    assert settings.cardd_enabled is False
    assert settings.vision_model in {"gpt-6-luna", settings.model_name}
    assert settings.vision_provider in {"openai", "google"}
