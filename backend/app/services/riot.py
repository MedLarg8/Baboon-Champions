from dataclasses import dataclass
from typing import Any
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
    def __init__(
        self,
        status_code: int,
        detail: str,
        *,
        retry_after_seconds: int | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.retry_after_seconds = retry_after_seconds
        super().__init__(detail)


class RiotAccountService:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = settings.riot_api_key
        self._regional_route = settings.riot_regional_route
        self._timeout = httpx.Timeout(8.0)
        self._transport = transport

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

        payload = await self._get_json(url, not_found_detail="Riot account not found.")
        try:
            puuid = payload["puuid"]
            canonical_game_name = payload["gameName"]
            canonical_tag_line = payload["tagLine"]
        except (KeyError, TypeError) as exc:
            raise RiotApiError(
                status.HTTP_502_BAD_GATEWAY,
                "Riot account response was missing required fields.",
            ) from exc

        return RiotAccount(
            puuid=puuid,
            game_name=canonical_game_name,
            tag_line=canonical_tag_line,
        )

    async def get_match_ids_by_puuid(
        self,
        puuid: str,
        *,
        queue_id: int,
        count: int,
    ) -> list[str]:
        encoded_puuid = quote(puuid, safe="")
        url = (
            f"https://{self._regional_route}.api.riotgames.com"
            f"/lol/match/v5/matches/by-puuid/{encoded_puuid}/ids"
        )
        payload = await self._get_json(
            url,
            params={"queue": str(queue_id), "start": "0", "count": str(count)},
            not_found_detail="Riot match history not found.",
        )
        if not isinstance(payload, list) or not all(isinstance(match_id, str) for match_id in payload):
            raise RiotApiError(
                status.HTTP_502_BAD_GATEWAY,
                "Riot match ID response was malformed.",
            )
        return payload

    async def get_match_details(self, match_id: str) -> dict[str, Any]:
        encoded_match_id = quote(match_id, safe="")
        url = (
            f"https://{self._regional_route}.api.riotgames.com"
            f"/lol/match/v5/matches/{encoded_match_id}"
        )
        payload = await self._get_json(url, not_found_detail="Riot match not found.")
        if not isinstance(payload, dict):
            raise RiotApiError(
                status.HTTP_502_BAD_GATEWAY,
                "Riot match response was malformed.",
            )
        return payload

    async def _get_json(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        not_found_detail: str,
    ) -> Any:
        if not self._api_key:
            raise RiotApiError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Riot API key is not configured.",
            )

        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers={"X-Riot-Token": self._api_key},
                )
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
            raise self._to_application_error(response, not_found_detail=not_found_detail)

        try:
            return response.json()
        except ValueError as exc:
            raise RiotApiError(
                status.HTTP_502_BAD_GATEWAY,
                "Riot response was not valid JSON.",
            ) from exc

    def _to_application_error(self, response: httpx.Response, *, not_found_detail: str) -> RiotApiError:
        riot_status_code = response.status_code
        if riot_status_code == status.HTTP_400_BAD_REQUEST:
            return RiotApiError(status.HTTP_400_BAD_REQUEST, "Invalid Riot ID request.")
        if riot_status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
            return RiotApiError(
                status.HTTP_502_BAD_GATEWAY,
                "Riot API key is invalid, missing, or expired.",
            )
        if riot_status_code == status.HTTP_404_NOT_FOUND:
            return RiotApiError(status.HTTP_404_NOT_FOUND, not_found_detail)
        if riot_status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            retry_after_seconds = _parse_retry_after(response.headers.get("Retry-After"))
            retry_message = (
                f" Riot asked clients to retry after {retry_after_seconds} seconds."
                if retry_after_seconds is not None
                else ""
            )
            return RiotApiError(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"Riot API rate limit reached. Try again later.{retry_message}",
                retry_after_seconds=retry_after_seconds,
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


def _parse_retry_after(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        retry_after = int(value)
    except ValueError:
        return None
    if retry_after < 0:
        return None
    return retry_after
