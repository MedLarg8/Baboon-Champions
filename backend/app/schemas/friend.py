from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class FriendCreate(BaseModel):
    display_name: str
    game_name: str
    tag_line: str

    @field_validator("display_name", "game_name", "tag_line", mode="before")
    @classmethod
    def trim_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("display_name", "game_name", "tag_line")
    @classmethod
    def require_non_empty(cls, value: str, info) -> str:
        if not value:
            field_name = info.field_name.replace("_", " ")
            raise ValueError(f"{field_name} cannot be empty.")
        return value


class FriendRead(BaseModel):
    id: int
    display_name: str
    game_name: str
    tag_line: str
    puuid: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
