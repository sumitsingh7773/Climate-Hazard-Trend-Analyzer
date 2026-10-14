import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mongodb_uri: str | None = None
    mongodb_database: str = "climate_hazard_analyzer"
    frontend_origin: str = "http://localhost:5173"
    api_rate_limit: str = "120/minute"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
