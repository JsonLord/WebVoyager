import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Web-Agent-Internal"
    API_V1_STR: str = "/api/v1"

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    BLABLADOR_API_KEY: str = os.getenv("BLABLADOR_API_KEY", "")

    # Session storage
    SESSIONS_DIR: str = "sessions_data"

    class Config:
        case_sensitive = True

settings = Settings()
