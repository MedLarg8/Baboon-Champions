from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.game import GameCreate, GameDeleteResponse, GameDetail, GameListResponse
from app.services.games import (
    FriendSelectionError,
    GameNotFoundError,
    GameValidationError,
    create_game,
    delete_game,
    get_game,
    list_games,
)

router = APIRouter(prefix="/games", tags=["games"])


@router.post("", response_model=GameDetail, status_code=status.HTTP_201_CREATED)
def create_manual_game(payload: GameCreate, db: Session = Depends(get_db)) -> GameDetail:
    try:
        return create_game(db, payload)
    except FriendSelectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GameValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("", response_model=GameListResponse)
def read_games(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> GameListResponse:
    return list_games(db, limit=limit, offset=offset)


@router.get("/{game_id}", response_model=GameDetail)
def read_game(game_id: int, db: Session = Depends(get_db)) -> GameDetail:
    try:
        return get_game(db, game_id)
    except GameNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete("/{game_id}", response_model=GameDeleteResponse)
def remove_game(game_id: int, db: Session = Depends(get_db)) -> GameDeleteResponse:
    try:
        delete_game(db, game_id)
    except GameNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return GameDeleteResponse(detail="Game deleted.")
