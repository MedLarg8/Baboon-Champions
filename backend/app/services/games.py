from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.friend import Friend
from app.models.game import Game, GameParticipant
from app.schemas.game import (
    CurrentBaboonGame,
    CurrentBaboonPlayer,
    CurrentBaboonResponse,
    GameCreate,
    GameDetail,
    GameListResponse,
    GameParticipantCreate,
    GameParticipantRead,
    GameSummary,
)


class GameValidationError(Exception):
    pass


class FriendSelectionError(Exception):
    pass


class GameNotFoundError(Exception):
    pass


def create_game(db: Session, payload: GameCreate) -> GameDetail:
    if len(payload.participants) < 2:
        raise GameValidationError("At least two players must be selected.")

    friend_ids = [participant.friend_id for participant in payload.participants]
    if len(set(friend_ids)) != len(friend_ids):
        raise GameValidationError("Players cannot appear twice in the same game.")

    champion_names = [_normalize_champion_name(participant.champion_name) for participant in payload.participants]
    if len(set(champion_names)) != len(champion_names):
        raise GameValidationError("Champions cannot be picked twice in the same game.")

    for participant in payload.participants:
        _validate_participant(participant)

    friends_by_id = _load_friends_by_id(db, friend_ids)
    missing_friend_ids = [friend_id for friend_id in friend_ids if friend_id not in friends_by_id]
    if missing_friend_ids:
        raise FriendSelectionError("One or more selected friends do not exist.")

    lowest_damage = min(participant.damage_to_champions for participant in payload.participants)
    game = Game(
        played_at=_ensure_utc(payload.played_at),
        notes=payload.notes,
    )
    db.add(game)
    db.flush()

    for participant in payload.participants:
        friend = friends_by_id[participant.friend_id]
        db.add(
            GameParticipant(
                game_id=game.id,
                friend_id=friend.id,
                display_name_snapshot=friend.display_name,
                game_name_snapshot=friend.game_name,
                tag_line_snapshot=friend.tag_line,
                champion_name=participant.champion_name.strip(),
                damage_to_champions=participant.damage_to_champions,
                is_baboon=participant.damage_to_champions == lowest_damage,
            ),
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise GameValidationError("Game could not be saved. Check the selected players and try again.") from exc

    db.refresh(game)
    return _to_game_detail(_load_game_or_raise(db, game.id))


def list_games(db: Session, *, limit: int, offset: int) -> GameListResponse:
    total = db.scalar(select(func.count()).select_from(Game)) or 0
    games = db.scalars(
        select(Game)
        .options(selectinload(Game.participants))
        .order_by(Game.played_at.desc(), Game.id.desc())
        .limit(limit)
        .offset(offset),
    ).all()

    return GameListResponse(
        items=[_to_game_summary(game) for game in games],
        limit=limit,
        offset=offset,
        total=total,
    )


def get_game(db: Session, game_id: int) -> GameDetail:
    return _to_game_detail(_load_game_or_raise(db, game_id))


def get_current_baboon(db: Session) -> CurrentBaboonResponse:
    game = db.scalar(
        select(Game)
        .options(selectinload(Game.participants))
        .order_by(Game.played_at.desc(), Game.id.desc()),
    )
    if game is None:
        return CurrentBaboonResponse(
            has_current_baboon=False,
            game=None,
            baboons=[],
        )

    return CurrentBaboonResponse(
        has_current_baboon=True,
        game=CurrentBaboonGame(
            id=game.id,
            played_at=_ensure_utc(game.played_at),
        ),
        baboons=[
            CurrentBaboonPlayer(
                friend_id=participant.friend_id,
                display_name=participant.display_name_snapshot,
                game_name=participant.game_name_snapshot,
                tag_line=participant.tag_line_snapshot,
                champion_name=participant.champion_name,
                damage_to_champions=participant.damage_to_champions,
            )
            for participant in _ordered_participants(game)
            if participant.is_baboon
        ],
    )


def delete_game(db: Session, game_id: int) -> None:
    game = db.get(Game, game_id)
    if game is None:
        raise GameNotFoundError("Game not found.")

    db.delete(game)
    db.commit()


def clear_deleted_friend_from_game_participants(db: Session, friend_id: int) -> None:
    db.execute(
        update(GameParticipant)
        .where(GameParticipant.friend_id == friend_id)
        .values(friend_id=None),
    )


def _validate_participant(participant: GameParticipantCreate) -> None:
    if not participant.champion_name.strip():
        raise GameValidationError("Every selected player must have a champion.")
    if participant.damage_to_champions < 0:
        raise GameValidationError("Damage must be zero or greater.")


def _normalize_champion_name(value: str) -> str:
    return value.strip().casefold()


def _load_friends_by_id(db: Session, friend_ids: list[int]) -> dict[int, Friend]:
    if not friend_ids:
        return {}
    friends = db.scalars(select(Friend).where(Friend.id.in_(friend_ids))).all()
    return {friend.id: friend for friend in friends}


def _load_game_or_raise(db: Session, game_id: int) -> Game:
    game = db.scalar(
        select(Game)
        .options(selectinload(Game.participants))
        .where(Game.id == game_id),
    )
    if game is None:
        raise GameNotFoundError("Game not found.")
    return game


def _to_game_summary(game: Game) -> GameSummary:
    participants = [_to_participant_read(participant) for participant in _ordered_participants(game)]
    baboons = [participant for participant in participants if participant.is_baboon]
    lowest_damage = min((participant.damage_to_champions for participant in participants), default=None)
    return GameSummary(
        id=game.id,
        played_at=_ensure_utc(game.played_at),
        created_at=_ensure_utc(game.created_at),
        updated_at=_ensure_utc(game.updated_at),
        notes=game.notes,
        player_count=len(participants),
        lowest_damage_to_champions=lowest_damage,
        participants=participants,
        baboons=baboons,
    )


def _to_game_detail(game: Game) -> GameDetail:
    return GameDetail(**_to_game_summary(game).model_dump())


def _to_participant_read(participant: GameParticipant) -> GameParticipantRead:
    return GameParticipantRead(
        id=participant.id,
        friend_id=participant.friend_id,
        display_name=participant.display_name_snapshot,
        game_name=participant.game_name_snapshot,
        tag_line=participant.tag_line_snapshot,
        champion_name=participant.champion_name,
        damage_to_champions=participant.damage_to_champions,
        is_baboon=participant.is_baboon,
    )


def _ordered_participants(game: Game) -> list[GameParticipant]:
    return sorted(
        game.participants,
        key=lambda participant: (
            -participant.damage_to_champions,
            participant.display_name_snapshot.casefold(),
            participant.id,
        ),
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
