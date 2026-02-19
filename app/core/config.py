import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Web-Agent-Internal"
    API_V1_STR: str = "/api/v1"

    # Blablador (Primary LLM Provider)
    BLABLADOR_API_KEY: str = os.getenv("BLABLADOR_API_KEY", "")
    BLABLADOR_BASE_URL: str = "https://api.helmholtz-blablador.fz-juelich.de/v1"

    # Optional OpenAI Key (Fallback or specific tasks)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Model Names (with underscores as requested)
    MODEL_LARGE: str = "alias_large"
    MODEL_FAST: str = "alias_fast"

    # Session storage
    SESSIONS_DIR: str = "sessions_data"

    class Config:
        case_sensitive = True

settings = Settings()
