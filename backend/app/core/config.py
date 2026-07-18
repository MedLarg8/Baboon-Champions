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
    match_lookback_per_friend: int = Field(default=10, alias="MATCH_LOOKBACK_PER_FRIEND", ge=1, le=100)
    match_sync_candidate_limit: int = Field(default=30, alias="MATCH_SYNC_CANDIDATE_LIMIT", ge=1, le=100)
    minimum_match_duration_seconds: int = Field(
        default=300,
        alias="MINIMUM_MATCH_DURATION_SECONDS",
        ge=0,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
