from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_riot_account_service
from app.api.errors import riot_http_exception
from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.schemas.match import MatchDetail, MatchListResponse, MatchSyncSummary
from app.services.matches import (
    MatchNotFoundError,
    get_imported_match,
    list_imported_matches,
    synchronize_matches,
)
from app.services.riot import RiotApiError, RiotAccountService

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/sync", response_model=MatchSyncSummary)
async def sync_matches(
    db: Session = Depends(get_db),
    riot_service: RiotAccountService = Depends(get_riot_account_service),
    settings: Settings = Depends(get_settings),
) -> MatchSyncSummary:
    try:
        return await synchronize_matches(db, riot_service, settings)
    except RiotApiError as exc:
        raise riot_http_exception(exc) from exc


@router.get("", response_model=MatchListResponse)
def read_matches(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> MatchListResponse:
    return list_imported_matches(db, limit=limit, offset=offset)


@router.get("/{match_id}", response_model=MatchDetail)
def read_match(match_id: int, db: Session = Depends(get_db)) -> MatchDetail:
    try:
        return get_imported_match(db, match_id)
    except MatchNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
