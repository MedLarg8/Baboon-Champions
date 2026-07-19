import httpx
import pytest

from app.core.config import Settings
from app.services.riot import RiotAccountService, RiotApiError


def make_settings(api_key: str | None = "test-key") -> Settings:
    return Settings(riot_api_key=api_key, riot_regional_route="europe")


@pytest.mark.anyio
async def test_resolve_account_by_riot_id_encodes_spaces_and_unicode() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={"puuid": "resolved-puuid", "gameName": "naami Player", "tagLine": "EUW"},
        )

    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(handler),
    )

    account = await service.resolve_account_by_riot_id("naami Player", "EUW")

    assert captured_request is not None
    assert "naami%20Player" in str(captured_request.url)
    assert account.puuid == "resolved-puuid"
    assert account.game_name == "naami Player"
    assert account.tag_line == "EUW"
    assert captured_request.headers["X-Riot-Token"] == "test-key"


@pytest.mark.anyio
async def test_resolve_account_rejects_malformed_success_payload() -> None:
    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"puuid": "missing names"})),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.resolve_account_by_riot_id("Name", "EUW")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Riot account response was missing required fields."


@pytest.mark.anyio
async def test_resolve_account_handles_non_json_error_body() -> None:
    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(lambda _: httpx.Response(404, text="<html>missing</html>")),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.resolve_account_by_riot_id("Missing", "EUW")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Riot account not found."


@pytest.mark.anyio
async def test_resolve_account_handles_missing_api_key() -> None:
    service = RiotAccountService(make_settings(api_key=None))

    with pytest.raises(RiotApiError) as exc_info:
        await service.resolve_account_by_riot_id("Name", "EUW")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Riot API key is not configured."


@pytest.mark.anyio
async def test_resolve_account_handles_expired_or_invalid_api_key() -> None:
    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(lambda _: httpx.Response(403, text="forbidden")),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.resolve_account_by_riot_id("Name", "EUW")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Riot API key is invalid, missing, or expired."


@pytest.mark.anyio
async def test_resolve_account_handles_rate_limit_retry_after() -> None:
    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(429, headers={"Retry-After": "7"}, text="too many"),
        ),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.resolve_account_by_riot_id("Name", "EUW")

    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after_seconds == 7
    assert "7 seconds" in exc_info.value.detail


@pytest.mark.anyio
async def test_resolve_account_handles_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=request)

    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.resolve_account_by_riot_id("Name", "EUW")

    assert exc_info.value.status_code == 504
    assert exc_info.value.detail == "Riot API request timed out. Try again later."


@pytest.mark.anyio
async def test_resolve_account_handles_unavailable_service() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.resolve_account_by_riot_id("Name", "EUW")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Unable to reach Riot services. Try again later."


@pytest.mark.anyio
async def test_resolve_account_handles_non_json_service_error_body() -> None:
    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(lambda _: httpx.Response(500, text="<html>broken</html>")),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.resolve_account_by_riot_id("Name", "EUW")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Riot service is unavailable. Try again later."
