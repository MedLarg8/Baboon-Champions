from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.match import CurrentBaboonResponse
from app.services.matches import get_current_baboon

router = APIRouter(prefix="/baboon", tags=["baboon"])


@router.get("/current", response_model=CurrentBaboonResponse)
def read_current_baboon(db: Session = Depends(get_db)) -> CurrentBaboonResponse:
    return get_current_baboon(db)
