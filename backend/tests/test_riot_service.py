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
            json={"puuid": "resolved-puuid", "gameName": "नामी Player", "tagLine": "EUW"},
        )

    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(handler),
    )

    account = await service.resolve_account_by_riot_id("नामी Player", "EUW")

    assert captured_request is not None
    assert "%E0%A4%A8%E0%A4%BE%E0%A4%AE%E0%A5%80%20Player" in str(captured_request.url)
    assert account.puuid == "resolved-puuid"
    assert account.game_name == "नामी Player"
    assert account.tag_line == "EUW"


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
async def test_get_match_ids_uses_queue_filter_and_configured_count() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json=["EUW1_1", "EUW1_2"])

    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(handler),
    )

    match_ids = await service.get_match_ids_by_puuid("friend puuid", queue_id=2400, count=10)

    assert match_ids == ["EUW1_1", "EUW1_2"]
    assert captured_request is not None
    assert "/lol/match/v5/matches/by-puuid/friend%20puuid/ids" in str(captured_request.url)
    assert captured_request.url.params["queue"] == "2400"
    assert captured_request.url.params["start"] == "0"
    assert captured_request.url.params["count"] == "10"
    assert captured_request.headers["X-Riot-Token"] == "test-key"


@pytest.mark.anyio
async def test_get_match_ids_bounds_count_and_start() -> None:
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(200, json=[])

    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(handler),
    )

    await service.get_match_ids_by_puuid("puuid", queue_id=2400, start=-5, count=500)

    assert captured_request is not None
    assert captured_request.url.params["start"] == "0"
    assert captured_request.url.params["count"] == "100"


@pytest.mark.anyio
async def test_get_match_details_returns_riot_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/lol/match/v5/matches/EUW1_123"
        return httpx.Response(200, json={"metadata": {"matchId": "EUW1_123"}, "info": {}})

    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(handler),
    )

    payload = await service.get_match_details("EUW1_123")

    assert payload["metadata"]["matchId"] == "EUW1_123"


@pytest.mark.anyio
async def test_get_match_details_rejects_malformed_success_payload() -> None:
    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"metadata": {}})),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.get_match_details("EUW1_123")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Riot match response was malformed."


@pytest.mark.anyio
async def test_match_service_handles_expired_or_invalid_api_key() -> None:
    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(lambda _: httpx.Response(403, text="forbidden")),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.get_match_details("EUW1_123")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Riot API key is invalid, missing, or expired."


@pytest.mark.anyio
async def test_match_service_handles_rate_limit_retry_after() -> None:
    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(
            lambda _: httpx.Response(429, headers={"Retry-After": "7"}, text="too many"),
        ),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.get_match_ids_by_puuid("puuid", queue_id=2400, count=10)

    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after_seconds == 7
    assert "7 seconds" in exc_info.value.detail


@pytest.mark.anyio
async def test_match_service_handles_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=request)

    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.get_match_details("EUW1_123")

    assert exc_info.value.status_code == 504
    assert exc_info.value.detail == "Riot API request timed out. Try again later."


@pytest.mark.anyio
async def test_match_service_handles_unavailable_service() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.get_match_ids_by_puuid("puuid", queue_id=2400, count=10)

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Unable to reach Riot services. Try again later."


@pytest.mark.anyio
async def test_match_service_handles_non_json_error_body() -> None:
    service = RiotAccountService(
        make_settings(),
        transport=httpx.MockTransport(lambda _: httpx.Response(500, text="<html>broken</html>")),
    )

    with pytest.raises(RiotApiError) as exc_info:
        await service.get_match_details("EUW1_123")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Riot service is unavailable. Try again later."
