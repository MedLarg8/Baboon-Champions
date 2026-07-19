from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    riot_api_key: str | None = Field(default=None, alias="RIOT_API_KEY")
    riot_regional_route: str = Field(default="europe", alias="RIOT_REGIONAL_ROUTE")
    database_url: str = Field(default="sqlite:///./aram_baboon.db", alias="DATABASE_URL")
    frontend_origin: str = Field(
        default="http://localhost:5173",
        alias="FRONTEND_ORIGIN",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def allowed_frontend_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]
        expanded_origins: list[str] = []

        for origin in origins:
            expanded_origins.append(origin)
            if origin == "http://localhost:5173":
                expanded_origins.append("http://127.0.0.1:5173")
            if origin == "http://127.0.0.1:5173":
                expanded_origins.append("http://localhost:5173")

        return list(dict.fromkeys(expanded_origins))


@lru_cache
def get_settings() -> Settings:
    return Settings()
