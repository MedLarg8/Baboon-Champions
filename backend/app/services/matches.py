from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models.friend import Friend
from app.models.match import Match, MatchParticipant
from app.schemas.match import (
    CurrentBaboonMatch,
    CurrentBaboonPlayer,
    CurrentBaboonResponse,
    MatchDetail,
    MatchListResponse,
    MatchParticipantRead,
    MatchSummary,
    MatchSyncSummary,
    SyncBaboonSummary,
)
from app.services.friends import list_friends
from app.services.riot import RiotApiError, RiotAccountService

ARAM_MAYHEM_QUEUE_ID = 2400


class MatchNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class ImportedParticipantCandidate:
    friend: Friend
    puuid: str
    champion_id: int | None
    champion_name: str | None
    team_id: int
    kills: int
    deaths: int
    assists: int
    damage_to_champions: int
    win: bool
    is_baboon: bool


@dataclass(frozen=True)
class ImportedMatchCandidate:
    riot_match_id: str
    queue_id: int
    game_creation: datetime | None
    game_start_time: datetime | None
    game_end_time: datetime
    duration_seconds: int
    game_version: str | None
    participants: list[ImportedParticipantCandidate]


async def synchronize_matches(
    db: Session,
    riot_service: RiotAccountService,
    settings: Settings,
) -> MatchSyncSummary:
    friends = list_friends(db)
    skipped_reasons: Counter[str] = Counter()
    imported_match_ids: list[str] = []

    if len(friends) < 2:
        skipped_reasons["not_enough_registered_friends"] += 1
        return _sync_summary(
            db,
            status="not_enough_friends",
            friends_checked=len(friends),
            candidate_match_ids=0,
            new_candidates_examined=0,
            matches_already_known=0,
            imported_match_ids=imported_match_ids,
            skipped_reasons=skipped_reasons,
        )

    candidate_match_ids = await _collect_candidate_match_ids(
        friends,
        riot_service,
        lookback_per_friend=settings.match_lookback_per_friend,
    )
    already_known_match_ids = _find_known_match_ids(db, candidate_match_ids)
    new_candidate_match_ids = [
        match_id for match_id in candidate_match_ids if match_id not in already_known_match_ids
    ][: settings.match_sync_candidate_limit]

    friends_by_puuid = {friend.puuid: friend for friend in friends}
    eligible_matches: list[ImportedMatchCandidate] = []

    for match_id in new_candidate_match_ids:
        try:
            riot_match = await riot_service.get_match_details(match_id)
        except RiotApiError as exc:
            if exc.status_code == 404:
                skipped_reasons["riot_match_not_found"] += 1
                continue
            raise

        candidate, skipped_reason = _build_import_candidate(
            riot_match,
            friends_by_puuid,
            minimum_duration_seconds=settings.minimum_match_duration_seconds,
        )
        if skipped_reason is not None:
            skipped_reasons[skipped_reason] += 1
            continue
        if candidate is not None:
            eligible_matches.append(candidate)

    eligible_matches.sort(key=lambda match: (match.game_end_time, match.riot_match_id))

    for candidate in eligible_matches:
        if _match_exists(db, candidate.riot_match_id):
            continue
        try:
            _persist_match_candidate(db, candidate)
        except IntegrityError:
            db.rollback()
            skipped_reasons["database_conflict"] += 1
            continue
        imported_match_ids.append(candidate.riot_match_id)

    if imported_match_ids:
        status = "completed"
    elif new_candidate_match_ids and skipped_reasons:
        status = "no_eligible_matches"
    else:
        status = "no_new_matches"

    return _sync_summary(
        db,
        status=status,
        friends_checked=len(friends),
        candidate_match_ids=len(candidate_match_ids),
        new_candidates_examined=len(new_candidate_match_ids),
        matches_already_known=len(already_known_match_ids),
        imported_match_ids=imported_match_ids,
        skipped_reasons=skipped_reasons,
    )


def list_imported_matches(db: Session, *, limit: int, offset: int) -> MatchListResponse:
    total = db.scalar(select(func.count()).select_from(Match)) or 0
    matches = db.scalars(
        select(Match)
        .options(selectinload(Match.participants))
        .order_by(Match.game_end_time.desc(), Match.id.desc())
        .offset(offset)
        .limit(limit),
    ).all()
    return MatchListResponse(
        items=[_to_match_summary(match) for match in matches],
        limit=limit,
        offset=offset,
        total=total,
    )


def get_imported_match(db: Session, match_id: int) -> MatchDetail:
    match = db.scalar(
        select(Match)
        .options(selectinload(Match.participants))
        .where(Match.id == match_id),
    )
    if match is None:
        raise MatchNotFoundError("Match not found.")
    return _to_match_detail(match)


def get_current_baboon(db: Session) -> CurrentBaboonResponse:
    match = db.scalar(
        select(Match)
        .options(selectinload(Match.participants))
        .order_by(Match.game_end_time.desc(), Match.id.desc())
        .limit(1),
    )
    if match is None:
        return CurrentBaboonResponse(
            has_current_baboon=False,
            match=None,
            baboons=[],
        )

    baboons = [
        CurrentBaboonPlayer(
            friend_id=participant.friend_id,
            display_name=participant.display_name_snapshot,
            game_name=participant.game_name_snapshot,
            tag_line=participant.tag_line_snapshot,
            champion_id=participant.champion_id,
            champion_name=participant.champion_name,
            kills=participant.kills,
            deaths=participant.deaths,
            assists=participant.assists,
            damage_to_champions=participant.damage_to_champions,
            win=participant.win,
        )
        for participant in _ordered_participants(match)
        if participant.is_baboon
    ]

    return CurrentBaboonResponse(
        has_current_baboon=bool(baboons),
        match=CurrentBaboonMatch(
            id=match.id,
            riot_match_id=match.riot_match_id,
            game_end_time=_ensure_utc(match.game_end_time),
            duration_seconds=match.duration_seconds,
        ),
        baboons=baboons,
    )


async def _collect_candidate_match_ids(
    friends: list[Friend],
    riot_service: RiotAccountService,
    *,
    lookback_per_friend: int,
) -> list[str]:
    seen: set[str] = set()
    candidate_match_ids: list[str] = []

    for friend in friends:
        friend_match_ids = await riot_service.get_match_ids_by_puuid(
            friend.puuid,
            queue_id=ARAM_MAYHEM_QUEUE_ID,
            count=lookback_per_friend,
        )
        for match_id in friend_match_ids:
            if match_id not in seen:
                seen.add(match_id)
                candidate_match_ids.append(match_id)

    return candidate_match_ids


def _find_known_match_ids(db: Session, candidate_match_ids: list[str]) -> set[str]:
    if not candidate_match_ids:
        return set()
    return set(
        db.scalars(
            select(Match.riot_match_id).where(Match.riot_match_id.in_(candidate_match_ids)),
        ).all(),
    )


def _match_exists(db: Session, riot_match_id: str) -> bool:
    return db.scalar(select(Match.id).where(Match.riot_match_id == riot_match_id)) is not None


def _build_import_candidate(
    riot_match: dict[str, Any],
    friends_by_puuid: dict[str, Friend],
    *,
    minimum_duration_seconds: int,
) -> tuple[ImportedMatchCandidate | None, str | None]:
    metadata = riot_match.get("metadata")
    info = riot_match.get("info")
    if not isinstance(metadata, dict) or not isinstance(info, dict):
        return None, "malformed_match"

    riot_match_id = metadata.get("matchId")
    if not isinstance(riot_match_id, str) or not riot_match_id:
        return None, "malformed_match"

    queue_id = _read_int(info.get("queueId"), default=-1)
    if queue_id != ARAM_MAYHEM_QUEUE_ID:
        return None, "not_aram_mayhem"

    duration_seconds = _read_duration_seconds(info)
    if duration_seconds is None:
        return None, "malformed_match"
    if duration_seconds < minimum_duration_seconds:
        return None, "match_too_short"

    riot_participants = info.get("participants")
    if not isinstance(riot_participants, list):
        return None, "malformed_match"

    registered_participants: list[ImportedParticipantCandidate] = []
    for participant in riot_participants:
        if not isinstance(participant, dict):
            continue
        if participant.get("puuid") not in friends_by_puuid:
            continue
        if _is_early_surrender(participant):
            return None, "early_surrender_or_remake"

        registered_participant, skipped_reason = _to_registered_participant(
            participant,
            friends_by_puuid,
        )
        if skipped_reason is not None:
            return None, skipped_reason
        if registered_participant is not None:
            registered_participants.append(registered_participant)

    if len(registered_participants) < 2:
        return None, "not_enough_registered_friends"

    team_ids = {participant.team_id for participant in registered_participants}
    if len(team_ids) != 1:
        return None, "registered_friends_on_multiple_teams"

    minimum_damage = min(participant.damage_to_champions for participant in registered_participants)
    participants_with_baboon_flags = [
        ImportedParticipantCandidate(
            friend=participant.friend,
            puuid=participant.puuid,
            champion_id=participant.champion_id,
            champion_name=participant.champion_name,
            team_id=participant.team_id,
            kills=participant.kills,
            deaths=participant.deaths,
            assists=participant.assists,
            damage_to_champions=participant.damage_to_champions,
            win=participant.win,
            is_baboon=participant.damage_to_champions == minimum_damage,
        )
        for participant in registered_participants
    ]

    game_start_time = _datetime_from_millis(info.get("gameStartTimestamp"))
    game_end_time = _datetime_from_millis(info.get("gameEndTimestamp"))
    if game_end_time is None and game_start_time is not None:
        game_end_time = game_start_time + timedelta(seconds=duration_seconds)
    if game_end_time is None:
        return None, "malformed_match"

    return (
        ImportedMatchCandidate(
            riot_match_id=riot_match_id,
            queue_id=queue_id,
            game_creation=_datetime_from_millis(info.get("gameCreation")),
            game_start_time=game_start_time,
            game_end_time=game_end_time,
            duration_seconds=duration_seconds,
            game_version=_read_optional_string(info.get("gameVersion")),
            participants=participants_with_baboon_flags,
        ),
        None,
    )


def _to_registered_participant(
    participant: dict[str, Any],
    friends_by_puuid: dict[str, Friend],
) -> tuple[ImportedParticipantCandidate | None, str | None]:
    puuid = participant.get("puuid")
    if not isinstance(puuid, str):
        return None, "malformed_match"
    friend = friends_by_puuid.get(puuid)
    if friend is None:
        return None, None

    damage_to_champions = _read_required_non_negative_int(
        participant.get("totalDamageDealtToChampions"),
    )
    if damage_to_champions is None:
        return None, "malformed_match"

    return (
        ImportedParticipantCandidate(
            friend=friend,
            puuid=puuid,
            champion_id=_read_optional_int(participant.get("championId")),
            champion_name=_read_optional_string(participant.get("championName")),
            team_id=_read_int(participant.get("teamId"), default=0),
            kills=_read_int(participant.get("kills"), default=0),
            deaths=_read_int(participant.get("deaths"), default=0),
            assists=_read_int(participant.get("assists"), default=0),
            damage_to_champions=damage_to_champions,
            win=bool(participant.get("win", False)),
            is_baboon=False,
        ),
        None,
    )


def _is_early_surrender(participant: dict[str, Any]) -> bool:
    return bool(participant.get("gameEndedInEarlySurrender", False))


def _read_duration_seconds(info: dict[str, Any]) -> int | None:
    raw_duration = info.get("gameDuration")
    if raw_duration is None:
        start_time = _datetime_from_millis(info.get("gameStartTimestamp"))
        end_time = _datetime_from_millis(info.get("gameEndTimestamp"))
        if start_time is None or end_time is None:
            return None
        return max(0, int((end_time - start_time).total_seconds()))

    duration = _read_int(raw_duration, default=-1)
    if duration < 0:
        return None
    if duration > 86_400:
        return duration // 1000
    return duration


def _datetime_from_millis(value: Any) -> datetime | None:
    if value is None:
        return None
    timestamp = _read_int(value, default=-1)
    if timestamp < 0:
        return None
    return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)


def _read_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_required_non_negative_int(value: Any) -> int | None:
    parsed_value = _read_optional_int(value)
    if parsed_value is None or parsed_value < 0:
        return None
    return parsed_value


def _read_optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _persist_match_candidate(db: Session, candidate: ImportedMatchCandidate) -> Match:
    match = Match(
        riot_match_id=candidate.riot_match_id,
        queue_id=candidate.queue_id,
        game_creation=candidate.game_creation,
        game_start_time=candidate.game_start_time,
        game_end_time=candidate.game_end_time,
        duration_seconds=candidate.duration_seconds,
        game_version=candidate.game_version,
    )
    db.add(match)
    db.flush()

    for participant in candidate.participants:
        db.add(
            MatchParticipant(
                match_id=match.id,
                friend_id=participant.friend.id,
                puuid_snapshot=participant.puuid,
                display_name_snapshot=participant.friend.display_name,
                game_name_snapshot=participant.friend.game_name,
                tag_line_snapshot=participant.friend.tag_line,
                champion_id=participant.champion_id,
                champion_name=participant.champion_name,
                team_id=participant.team_id,
                kills=participant.kills,
                deaths=participant.deaths,
                assists=participant.assists,
                damage_to_champions=participant.damage_to_champions,
                win=participant.win,
                is_baboon=participant.is_baboon,
            ),
        )

    db.commit()
    db.refresh(match)
    return match


def _sync_summary(
    db: Session,
    *,
    status: str,
    friends_checked: int,
    candidate_match_ids: int,
    new_candidates_examined: int,
    matches_already_known: int,
    imported_match_ids: list[str],
    skipped_reasons: Counter[str],
) -> MatchSyncSummary:
    current = get_current_baboon(db)
    return MatchSyncSummary(
        status=status,
        friends_checked=friends_checked,
        candidate_match_ids=candidate_match_ids,
        new_candidates_examined=new_candidates_examined,
        matches_imported=len(imported_match_ids),
        matches_already_known=matches_already_known,
        matches_skipped=sum(skipped_reasons.values()),
        skipped_reasons=dict(skipped_reasons),
        imported_match_ids=imported_match_ids,
        current_baboons=[
            SyncBaboonSummary(
                display_name=baboon.display_name,
                damage_to_champions=baboon.damage_to_champions,
            )
            for baboon in current.baboons
        ],
    )


def _to_match_summary(match: Match) -> MatchSummary:
    participants = [_to_participant_read(participant) for participant in _ordered_participants(match)]
    baboons = [participant for participant in participants if participant.is_baboon]
    lowest_damage = min((participant.damage_to_champions for participant in participants), default=None)
    team_won = participants[0].win if participants else None
    return MatchSummary(
        id=match.id,
        riot_match_id=match.riot_match_id,
        queue_id=match.queue_id,
        game_end_time=_ensure_utc(match.game_end_time),
        duration_seconds=match.duration_seconds,
        game_version=match.game_version,
        registered_friend_count=len(participants),
        team_won=team_won,
        lowest_damage_to_champions=lowest_damage,
        participants=participants,
        baboons=baboons,
    )


def _to_match_detail(match: Match) -> MatchDetail:
    participants = [_to_participant_read(participant) for participant in _ordered_participants(match)]
    return MatchDetail(
        id=match.id,
        riot_match_id=match.riot_match_id,
        queue_id=match.queue_id,
        game_creation=_ensure_optional_utc(match.game_creation),
        game_start_time=_ensure_optional_utc(match.game_start_time),
        game_end_time=_ensure_utc(match.game_end_time),
        duration_seconds=match.duration_seconds,
        game_version=match.game_version,
        imported_at=_ensure_utc(match.imported_at),
        participants=participants,
        baboons=[participant for participant in participants if participant.is_baboon],
    )


def _ordered_participants(match: Match) -> list[MatchParticipant]:
    return sorted(
        match.participants,
        key=lambda participant: (-participant.damage_to_champions, participant.id),
    )


def _to_participant_read(participant: MatchParticipant) -> MatchParticipantRead:
    return MatchParticipantRead(
        id=participant.id,
        friend_id=participant.friend_id,
        display_name=participant.display_name_snapshot,
        game_name=participant.game_name_snapshot,
        tag_line=participant.tag_line_snapshot,
        champion_id=participant.champion_id,
        champion_name=participant.champion_name,
        team_id=participant.team_id,
        kills=participant.kills,
        deaths=participant.deaths,
        assists=participant.assists,
        damage_to_champions=participant.damage_to_champions,
        win=participant.win,
        is_baboon=participant.is_baboon,
    )


def _ensure_optional_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return _ensure_utc(value)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
