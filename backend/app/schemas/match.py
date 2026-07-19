from datetime import datetime

from pydantic import BaseModel


class MatchParticipantRead(BaseModel):
    id: int
    friend_id: int | None
    display_name: str
    game_name: str
    tag_line: str
    champion_id: int | None
    champion_name: str | None
    team_id: int
    kills: int
    deaths: int
    assists: int
    damage_to_champions: int
    win: bool
    is_baboon: bool


class MatchSummary(BaseModel):
    id: int
    riot_match_id: str
    queue_id: int
    game_end_time: datetime
    duration_seconds: int
    game_version: str | None
    registered_friend_count: int
    team_won: bool | None
    lowest_damage_to_champions: int | None
    participants: list[MatchParticipantRead]
    baboons: list[MatchParticipantRead]


class MatchListResponse(BaseModel):
    items: list[MatchSummary]
    limit: int
    offset: int
    total: int


class MatchDetail(BaseModel):
    id: int
    riot_match_id: str
    queue_id: int
    game_creation: datetime | None
    game_start_time: datetime | None
    game_end_time: datetime
    duration_seconds: int
    game_version: str | None
    imported_at: datetime
    participants: list[MatchParticipantRead]
    baboons: list[MatchParticipantRead]


class CurrentBaboonMatch(BaseModel):
    id: int
    riot_match_id: str
    game_end_time: datetime
    duration_seconds: int


class CurrentBaboonPlayer(BaseModel):
    friend_id: int | None
    display_name: str
    game_name: str
    tag_line: str
    champion_id: int | None
    champion_name: str | None
    kills: int
    deaths: int
    assists: int
    damage_to_champions: int
    win: bool


class CurrentBaboonResponse(BaseModel):
    has_current_baboon: bool
    match: CurrentBaboonMatch | None
    baboons: list[CurrentBaboonPlayer]


class SyncBaboonSummary(BaseModel):
    display_name: str
    damage_to_champions: int


class MatchSyncSummary(BaseModel):
    status: str
    friends_checked: int
    candidate_match_ids: int
    new_candidates_examined: int
    matches_imported: int
    matches_already_known: int
    matches_skipped: int
    skipped_reasons: dict[str, int]
    imported_match_ids: list[str]
    current_baboons: list[SyncBaboonSummary]
