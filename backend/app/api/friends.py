from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_riot_account_service
from app.api.errors import riot_http_exception
from app.database.session import get_db
from app.schemas.friend import FriendCreate, FriendRead
from app.services.friends import (
    FriendAlreadyExistsError,
    FriendNotFoundError,
    create_friend,
    delete_friend,
    list_friends,
)
from app.services.riot import RiotApiError, RiotAccountService

router = APIRouter(prefix="/friends", tags=["friends"])


@router.get("", response_model=list[FriendRead])
def read_friends(db: Session = Depends(get_db)) -> list[FriendRead]:
    return list_friends(db)


@router.post("", response_model=FriendRead, status_code=status.HTTP_201_CREATED)
async def register_friend(
    payload: FriendCreate,
    db: Session = Depends(get_db),
    riot_service: RiotAccountService = Depends(get_riot_account_service),
) -> FriendRead:
    try:
        return await create_friend(db, payload, riot_service)
    except FriendAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except RiotApiError as exc:
        raise riot_http_exception(exc) from exc


@router.delete("/{friend_id}", status_code=status.HTTP_200_OK)
def remove_friend(friend_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        delete_friend(db, friend_id)
    except FriendNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return {"detail": "Friend deleted."}
