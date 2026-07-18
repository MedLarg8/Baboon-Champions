from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.riot import RiotAccountService


def get_riot_account_service(
    settings: Settings = Depends(get_settings),
) -> RiotAccountService:
    return RiotAccountService(settings)
