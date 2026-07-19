from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class GameParticipantCreate(BaseModel):
    friend_id: int
    champion_name: str
    damage_to_champions: int = Field(ge=0)

    @field_validator("champion_name", mode="before")
    @classmethod
    def trim_champion(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("champion_name")
    @classmethod
    def require_champion(cls, value: str) -> str:
        if not value:
            raise ValueError("champion name cannot be empty.")
        return value


class GameCreate(BaseModel):
    played_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str | None = None
    participants: list[GameParticipantCreate]

    @field_validator("notes", mode="before")
    @classmethod
    def trim_notes(cls, value: object) -> object:
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value


class GameParticipantRead(BaseModel):
    id: int
    friend_id: int | None
    display_name: str
    game_name: str
    tag_line: str
    champion_name: str
    damage_to_champions: int
    is_baboon: bool


class GameSummary(BaseModel):
    id: int
    played_at: datetime
    created_at: datetime
    updated_at: datetime
    notes: str | None
    player_count: int
    lowest_damage_to_champions: int | None
    participants: list[GameParticipantRead]
    baboons: list[GameParticipantRead]


class GameListResponse(BaseModel):
    items: list[GameSummary]
    limit: int
    offset: int
    total: int


class GameDetail(GameSummary):
    pass


class CurrentBaboonGame(BaseModel):
    id: int
    played_at: datetime


class CurrentBaboonPlayer(BaseModel):
    friend_id: int | None
    display_name: str
    game_name: str
    tag_line: str
    champion_name: str
    damage_to_champions: int


class CurrentBaboonResponse(BaseModel):
    has_current_baboon: bool
    game: CurrentBaboonGame | None
    baboons: list[CurrentBaboonPlayer]


class GameDeleteResponse(BaseModel):
    detail: str
