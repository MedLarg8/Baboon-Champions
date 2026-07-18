from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.friend import Friend
from app.schemas.friend import FriendCreate
from app.services.riot import RiotAccount, RiotAccountService


class FriendAlreadyExistsError(Exception):
    pass


class FriendNotFoundError(Exception):
    pass


def normalize_riot_part(value: str) -> str:
    return value.strip().casefold()


def list_friends(db: Session) -> list[Friend]:
    return list(
        db.scalars(
            select(Friend).order_by(Friend.created_at.asc(), Friend.id.asc()),
        ).all(),
    )


async def create_friend(
    db: Session,
    payload: FriendCreate,
    riot_service: RiotAccountService,
) -> Friend:
    account = await riot_service.resolve_account_by_riot_id(
        payload.game_name,
        payload.tag_line,
    )
    ensure_friend_is_new(db, account)

    friend = Friend(
        display_name=payload.display_name,
        game_name=account.game_name,
        tag_line=account.tag_line,
        normalized_game_name=normalize_riot_part(account.game_name),
        normalized_tag_line=normalize_riot_part(account.tag_line),
        puuid=account.puuid,
    )
    db.add(friend)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise FriendAlreadyExistsError("This Riot account is already registered.") from exc

    db.refresh(friend)
    return friend


def ensure_friend_is_new(db: Session, account: RiotAccount) -> None:
    existing_puuid = db.scalar(select(Friend).where(Friend.puuid == account.puuid))
    if existing_puuid is not None:
        raise FriendAlreadyExistsError("This Riot account is already registered.")

    normalized_game_name = normalize_riot_part(account.game_name)
    normalized_tag_line = normalize_riot_part(account.tag_line)
    existing_riot_id = db.scalar(
        select(Friend).where(
            Friend.normalized_game_name == normalized_game_name,
            Friend.normalized_tag_line == normalized_tag_line,
        ),
    )
    if existing_riot_id is not None:
        raise FriendAlreadyExistsError("This Riot ID is already registered.")


def delete_friend(db: Session, friend_id: int) -> None:
    friend = db.get(Friend, friend_id)
    if friend is None:
        raise FriendNotFoundError("Friend not found.")

    db.delete(friend)
    db.commit()
