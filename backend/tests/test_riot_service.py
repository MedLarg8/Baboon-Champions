import httpx
import pytest

from app.core.config import Settings
from app.services.riot import RiotAccountService, RiotApiError


def make_settings(api_key: str | None = "test-key") -> Settings:
    return Settings(riot_api_key=api_key, riot_regional_route="europe")


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
