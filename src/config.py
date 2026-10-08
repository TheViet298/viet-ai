from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI20K Agent"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000"

    # LLM Configuration (Google Gemini & OpenAI)
    google_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    model: str = ""
    model_name: str = "gemini-2.5-flash"
    # Vision Configuration (GPT-6-Luna & Google)
    vision_provider: Literal["openai", "google"] = "openai"
    vision_model: str = "gpt-6-luna"
    cardd_enabled: bool = False
    dashboard_vision_enabled: bool = True
    dashboard_vision_model: str = "gemini-3.5-flash"
    dashboard_vision_timeout_s: float = Field(default=25, gt=0, le=60)
    image_routing_timeout_s: float = Field(default=12, gt=0, le=30)
    image_routing_min_confidence: float = Field(default=.8, ge=0, le=1)
    cardd_python_executable: str = ""
    cardd_inference_timeout_s: float = Field(default=45, gt=0, le=60)
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Database
    database_url: str = "sqlite:///./data/app.db"

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"
    agent_llm_enabled: bool = True
    agent_turn_timeout_s: float = Field(default=20, gt=0, le=60)
    agent_llm_timeout_s: float = Field(default=12, gt=0, le=30)
    rag_retrieval_timeout_s: float = Field(default=5, gt=0, le=20)
    agent_circuit_cooldown_s: float = Field(default=60, ge=1)
    rag_max_distance: float = Field(default=0.70, ge=0.0)
    rag_context_max_bytes: int = Field(default=6000, gt=0)
    agent_context_max_bytes: int = Field(default=8000, gt=0)
    customer_demo_token: str = ""
    staff_demo_token: str = ""
    service_points_file: str = "./fixtures/service_points.demo.json"

    @model_validator(mode="after")
    def validate_context_budgets(self):
        if self.rag_context_max_bytes > self.agent_context_max_bytes:
            raise ValueError("RAG evidence budget exceeds prompt budget")
        if self.model:
            self.model_name = self.model
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
