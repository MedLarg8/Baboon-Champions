from dataclasses import dataclass
from urllib.parse import quote

import httpx
from fastapi import status

from app.core.config import Settings


@dataclass(frozen=True)
class RiotAccount:
    puuid: str
    game_name: str
    tag_line: str


class RiotApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class RiotAccountService:
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.riot_api_key
        self._regional_route = settings.riot_regional_route
        self._timeout = httpx.Timeout(8.0)

    async def resolve_account_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
    ) -> RiotAccount:
        if not self._api_key:
            raise RiotApiError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Riot API key is not configured.",
            )

        encoded_game_name = quote(game_name, safe="")
        encoded_tag_line = quote(tag_line, safe="")
        url = (
            f"https://{self._regional_route}.api.riotgames.com"
            f"/riot/account/v1/accounts/by-riot-id/{encoded_game_name}/{encoded_tag_line}"
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers={"X-Riot-Token": self._api_key})
        except httpx.TimeoutException as exc:
            raise RiotApiError(
                status.HTTP_504_GATEWAY_TIMEOUT,
                "Riot API request timed out. Try again later.",
            ) from exc
        except httpx.RequestError as exc:
            raise RiotApiError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Unable to reach Riot services. Try again later.",
            ) from exc

        if response.status_code != status.HTTP_200_OK:
            raise self._to_application_error(response.status_code)

        payload = response.json()
        try:
            puuid = payload["puuid"]
            canonical_game_name = payload["gameName"]
            canonical_tag_line = payload["tagLine"]
        except KeyError as exc:
            raise RiotApiError(
                status.HTTP_502_BAD_GATEWAY,
                "Riot account response was missing required fields.",
            ) from exc

        return RiotAccount(
            puuid=puuid,
            game_name=canonical_game_name,
            tag_line=canonical_tag_line,
        )

    def _to_application_error(self, riot_status_code: int) -> RiotApiError:
        if riot_status_code == status.HTTP_400_BAD_REQUEST:
            return RiotApiError(status.HTTP_400_BAD_REQUEST, "Invalid Riot ID request.")
        if riot_status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            return RiotApiError(
                status.HTTP_502_BAD_GATEWAY,
                "Riot API key is invalid, missing, or expired.",
            )
        if riot_status_code == status.HTTP_404_NOT_FOUND:
            return RiotApiError(status.HTTP_404_NOT_FOUND, "Riot account not found.")
        if riot_status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            return RiotApiError(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Riot API rate limit reached. Try again later.",
            )
        if riot_status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            return RiotApiError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Riot service is unavailable. Try again later.",
            )
        return RiotApiError(
            status.HTTP_502_BAD_GATEWAY,
            "Unable to resolve Riot account right now.",
        )
