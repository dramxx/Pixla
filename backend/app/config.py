from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    db_path: str = "./pixla.db"
    storage_path: str = "./storage"

    # Diffusion model (for reference image generation)
    model_id: str = "runwayml/stable-diffusion-v1-5"
    model_device: str = "cuda"
    model_dtype: str = "float16"
    model_default_steps: int = 20
    model_default_guidance: float = 7.5
    reference_size: int = 512

    # Local LLM (for agent pixel drawing)
    llm_host: str = "localhost"
    llm_port: int = 8080
    llm_model: str = "llama3"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    llm_timeout: float = 120.0
    max_iterations: int = 40

    # System prompt for agent
    system_prompt: Optional[str] = None

    # API keys (optional fallback)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
