from collections.abc import Generator
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_riot_account_service
from app.database.session import Base, create_database_engine, get_db
from app.main import create_app
from app.models.friend import Friend
from app.models.match import Match
from app.services.friends import normalize_riot_part
from app.services.riot import RiotAccount, RiotApiError


class FakeRiotService:
    def __init__(self) -> None:
        self.account = RiotAccount(
            puuid="account-puuid",
            game_name="Windshitter",
            tag_line="EUW",
        )
        self.account_error: RiotApiError | None = None
        self.match_ids_error: RiotApiError | None = None
        self.match_ids_by_puuid: dict[str, list[str]] = {}
        self.match_details_by_id: dict[str, dict[str, Any] | RiotApiError] = {}
        self.match_id_calls: list[tuple[str, int, int]] = []
        self.match_detail_calls: list[str] = []

    async def resolve_account_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
    ) -> RiotAccount:
        if self.account_error is not None:
            raise self.account_error
        return self.account

    async def get_match_ids_by_puuid(
        self,
        puuid: str,
        *,
        queue_id: int,
        start: int = 0,
        count: int,
    ) -> list[str]:
        self.match_id_calls.append((puuid, queue_id, count))
        if self.match_ids_error is not None:
            raise self.match_ids_error
        return self.match_ids_by_puuid.get(puuid, [])

    async def get_match_details(self, match_id: str) -> dict[str, Any]:
        self.match_detail_calls.append(match_id)
        detail = self.match_details_by_id[match_id]
        if isinstance(detail, RiotApiError):
            raise detail
        return deepcopy(detail)


@pytest.fixture()
def client(tmp_path) -> Generator[
    tuple[TestClient, FakeRiotService, sessionmaker[Session]],
    None,
    None,
]:
    app = create_app(initialize_database=False)
    db_path = tmp_path / "matches.db"
    engine = create_database_engine(
        f"sqlite:///{db_path.as_posix()}",
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    riot_service = FakeRiotService()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    def override_riot_service() -> FakeRiotService:
        return riot_service

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_riot_account_service] = override_riot_service

    with TestClient(app) as test_client:
        yield test_client, riot_service, testing_session_local

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def add_friend(
    session_factory: sessionmaker[Session],
    *,
    display_name: str,
    game_name: str,
    tag_line: str,
    puuid: str,
) -> Friend:
    with session_factory() as db:
        friend = Friend(
            display_name=display_name,
            game_name=game_name,
            tag_line=tag_line,
            normalized_game_name=normalize_riot_part(game_name),
            normalized_tag_line=normalize_riot_part(tag_line),
            puuid=puuid,
        )
        db.add(friend)
        db.commit()
        db.refresh(friend)
        db.expunge(friend)
        return friend


def add_default_friends(session_factory: sessionmaker[Session]) -> tuple[Friend, Friend]:
    return (
        add_friend(
            session_factory,
            display_name="Mohamed",
            game_name="Windshitter",
            tag_line="EUW",
            puuid="friend-puuid-1",
        ),
        add_friend(
            session_factory,
            display_name="Ahmed",
            game_name="Rock",
            tag_line="EUW",
            puuid="friend-puuid-2",
        ),
    )


def match_payload(
    match_id: str,
    *,
    queue_id: int = 2400,
    start_ms: int = 1_784_385_000_000,
    duration_seconds: int = 1200,
    participants: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    participants = participants or [
        participant_payload(
            "friend-puuid-1",
            champion_name="Brand",
            damage=52140,
            kills=18,
            deaths=12,
            assists=31,
        ),
        participant_payload(
            "friend-puuid-2",
            champion_id=54,
            champion_name="Malphite",
            damage=13482,
            kills=4,
            deaths=17,
            assists=21,
        ),
        participant_payload(
            "random-puuid-1",
            champion_name="Ashe",
            damage=9000,
            kills=11,
            deaths=13,
            assists=24,
        ),
    ]
    return {
        "metadata": {
            "matchId": match_id,
            "participants": [participant["puuid"] for participant in participants],
        },
        "info": {
            "gameCreation": start_ms,
            "gameStartTimestamp": start_ms,
            "gameEndTimestamp": start_ms + (duration_seconds * 1000),
            "gameDuration": duration_seconds,
            "gameVersion": "26.14.1",
            "queueId": queue_id,
            "participants": participants,
        },
    }


def participant_payload(
    puuid: str,
    *,
    champion_id: int = 63,
    champion_name: str = "Brand",
    team_id: int = 100,
    damage: int = 20000,
    kills: int = 5,
    deaths: int = 5,
    assists: int = 20,
    win: bool = True,
    early_surrender: bool = False,
) -> dict[str, Any]:
    return {
        "puuid": puuid,
        "championId": champion_id,
        "championName": champion_name,
        "teamId": team_id,
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "totalDamageDealtToChampions": damage,
        "win": win,
        "gameEndedInEarlySurrender": early_surrender,
    }


def configure_match(
    riot_service: FakeRiotService,
    *,
    match_id: str = "EUW1_123",
    payload: dict[str, Any] | None = None,
) -> None:
    riot_service.match_ids_by_puuid = {
        "friend-puuid-1": [match_id],
        "friend-puuid-2": [match_id],
    }
    riot_service.match_details_by_id = {
        match_id: payload or match_payload(match_id),
    }


def test_sync_requires_at_least_two_registered_friends(client) -> None:
    test_client, riot_service, session_factory = client
    add_friend(
        session_factory,
        display_name="Mohamed",
        game_name="Windshitter",
        tag_line="EUW",
        puuid="friend-puuid-1",
    )

    response = test_client.post("/api/matches/sync")

    assert response.status_code == 200
    assert response.json()["status"] == "not_enough_friends"
    assert response.json()["skipped_reasons"] == {"not_enough_registered_friends": 1}
    assert riot_service.match_id_calls == []


def test_sync_deduplicates_imports_match_and_excludes_randoms(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    configure_match(riot_service)

    response = test_client.post("/api/matches/sync")

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_match_ids"] == 1
    assert payload["new_candidates_examined"] == 1
    assert payload["matches_imported"] == 1
    assert riot_service.match_detail_calls == ["EUW1_123"]

    match_response = test_client.get("/api/matches").json()["items"][0]
    assert match_response["registered_friend_count"] == 2
    assert {participant["display_name"] for participant in match_response["participants"]} == {
        "Mohamed",
        "Ahmed",
    }
    assert match_response["baboons"][0]["display_name"] == "Ahmed"
    assert match_response["lowest_damage_to_champions"] == 13482


def test_sync_ignores_already_imported_match_ids_and_is_idempotent(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    configure_match(riot_service)

    first_response = test_client.post("/api/matches/sync")
    second_response = test_client.post("/api/matches/sync")

    assert first_response.json()["matches_imported"] == 1
    assert second_response.json()["matches_imported"] == 0
    assert second_response.json()["matches_already_known"] == 1
    assert riot_service.match_detail_calls == ["EUW1_123"]
    assert len(test_client.get("/api/matches").json()["items"]) == 1


def test_sync_rejects_ordinary_aram_queue_after_fetching_detail(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    configure_match(riot_service, payload=match_payload("EUW1_123", queue_id=450))

    response = test_client.post("/api/matches/sync")

    assert response.status_code == 200
    assert response.json()["matches_imported"] == 0
    assert response.json()["skipped_reasons"] == {"not_aram_mayhem": 1}


def test_sync_missing_damage_value_skips_candidate(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    missing_damage_participant = participant_payload("friend-puuid-2", damage=9000)
    del missing_damage_participant["totalDamageDealtToChampions"]
    configure_match(
        riot_service,
        payload=match_payload(
            "EUW1_missing_damage",
            participants=[
                participant_payload("friend-puuid-1", damage=10000),
                missing_damage_participant,
            ],
        ),
        match_id="EUW1_missing_damage",
    )

    response = test_client.post("/api/matches/sync")

    assert response.json()["matches_imported"] == 0
    assert response.json()["skipped_reasons"] == {"malformed_match": 1}
    assert test_client.get("/api/matches").json()["items"] == []


def test_sync_missing_optional_early_surrender_field_does_not_crash(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    first_participant = participant_payload("friend-puuid-1", damage=10000)
    second_participant = participant_payload("friend-puuid-2", damage=9000)
    del first_participant["gameEndedInEarlySurrender"]
    del second_participant["gameEndedInEarlySurrender"]
    configure_match(
        riot_service,
        payload=match_payload(
            "EUW1_missing_surrender",
            participants=[first_participant, second_participant],
        ),
        match_id="EUW1_missing_surrender",
    )

    response = test_client.post("/api/matches/sync")

    assert response.json()["matches_imported"] == 1


def test_sync_random_early_surrender_does_not_skip_registered_result(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    configure_match(
        riot_service,
        payload=match_payload(
            "EUW1_random_surrender",
            participants=[
                participant_payload("friend-puuid-1", damage=10000),
                participant_payload("friend-puuid-2", damage=9000),
                participant_payload("random-puuid-1", damage=5000, early_surrender=True),
            ],
        ),
        match_id="EUW1_random_surrender",
    )

    response = test_client.post("/api/matches/sync")

    assert response.json()["matches_imported"] == 1


def test_sync_requires_two_registered_friends_in_match(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    configure_match(
        riot_service,
        payload=match_payload(
            "EUW1_123",
            participants=[
                participant_payload("friend-puuid-1", damage=10000),
                participant_payload("random-puuid-1", damage=5000),
            ],
        ),
    )

    response = test_client.post("/api/matches/sync")

    assert response.json()["skipped_reasons"] == {"not_enough_registered_friends": 1}
    assert test_client.get("/api/matches").json()["items"] == []


def test_sync_skips_registered_friends_on_different_teams(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    configure_match(
        riot_service,
        payload=match_payload(
            "EUW1_123",
            participants=[
                participant_payload("friend-puuid-1", team_id=100, damage=10000),
                participant_payload("friend-puuid-2", team_id=200, damage=9000),
            ],
        ),
    )

    response = test_client.post("/api/matches/sync")

    assert response.json()["skipped_reasons"] == {"registered_friends_on_multiple_teams": 1}


def test_sync_skips_short_and_early_surrender_matches(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    riot_service.match_ids_by_puuid = {
        "friend-puuid-1": ["EUW1_short", "EUW1_surrender"],
        "friend-puuid-2": ["EUW1_short", "EUW1_surrender"],
    }
    riot_service.match_details_by_id = {
        "EUW1_short": match_payload("EUW1_short", duration_seconds=240),
        "EUW1_surrender": match_payload(
            "EUW1_surrender",
            participants=[
                participant_payload("friend-puuid-1", damage=10000),
                participant_payload("friend-puuid-2", damage=9000, early_surrender=True),
            ],
        ),
    }

    response = test_client.post("/api/matches/sync")

    assert response.json()["matches_imported"] == 0
    assert response.json()["skipped_reasons"] == {
        "match_too_short": 1,
        "early_surrender_or_remake": 1,
    }


def test_sync_marks_tied_co_baboons_and_current_returns_all(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    configure_match(
        riot_service,
        payload=match_payload(
            "EUW1_tie",
            participants=[
                participant_payload("friend-puuid-1", champion_name="Brand", damage=12000),
                participant_payload("friend-puuid-2", champion_name="Malphite", damage=12000),
            ],
        ),
        match_id="EUW1_tie",
    )

    sync_response = test_client.post("/api/matches/sync").json()
    current_response = test_client.get("/api/baboon/current").json()

    assert sync_response["matches_imported"] == 1
    assert len(sync_response["current_baboons"]) == 2
    assert current_response["has_current_baboon"] is True
    assert current_response["match"]["duration_seconds"] == 1200
    assert {baboon["display_name"] for baboon in current_response["baboons"]} == {
        "Mohamed",
        "Ahmed",
    }


def test_sync_imports_multiple_matches_and_lists_newest_first(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    riot_service.match_ids_by_puuid = {
        "friend-puuid-1": ["EUW1_new", "EUW1_old"],
        "friend-puuid-2": ["EUW1_old", "EUW1_new"],
    }
    riot_service.match_details_by_id = {
        "EUW1_old": match_payload("EUW1_old", start_ms=1_784_300_000_000),
        "EUW1_new": match_payload("EUW1_new", start_ms=1_784_400_000_000),
    }

    sync_response = test_client.post("/api/matches/sync").json()
    matches_response = test_client.get("/api/matches").json()

    assert sync_response["matches_imported"] == 2
    assert sync_response["imported_match_ids"] == ["EUW1_old", "EUW1_new"]
    assert [match["riot_match_id"] for match in matches_response["items"]] == ["EUW1_new", "EUW1_old"]


def test_match_list_applies_pagination(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    riot_service.match_ids_by_puuid = {
        "friend-puuid-1": ["EUW1_3", "EUW1_2", "EUW1_1"],
        "friend-puuid-2": ["EUW1_3", "EUW1_2", "EUW1_1"],
    }
    riot_service.match_details_by_id = {
        "EUW1_1": match_payload("EUW1_1", start_ms=1_784_300_000_000),
        "EUW1_2": match_payload("EUW1_2", start_ms=1_784_400_000_000),
        "EUW1_3": match_payload("EUW1_3", start_ms=1_784_500_000_000),
    }
    test_client.post("/api/matches/sync")

    response = test_client.get("/api/matches?limit=1&offset=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert payload["total"] == 3
    assert payload["items"][0]["riot_match_id"] == "EUW1_2"


def test_match_detail_and_missing_match(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    configure_match(riot_service)
    test_client.post("/api/matches/sync")
    match_id = test_client.get("/api/matches").json()["items"][0]["id"]

    detail_response = test_client.get(f"/api/matches/{match_id}")
    missing_response = test_client.get("/api/matches/999")

    assert detail_response.status_code == 200
    assert detail_response.json()["riot_match_id"] == "EUW1_123"
    assert detail_response.json()["participants"][0]["damage_to_champions"] == 52140
    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Match not found."}


def test_current_baboon_empty_before_history_exists(client) -> None:
    test_client, _, _ = client

    response = test_client.get("/api/baboon/current")

    assert response.status_code == 200
    assert response.json() == {
        "has_current_baboon": False,
        "match": None,
        "baboons": [],
    }


def test_sync_continues_past_malformed_candidate(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    riot_service.match_ids_by_puuid = {
        "friend-puuid-1": ["EUW1_bad", "EUW1_good"],
        "friend-puuid-2": ["EUW1_bad", "EUW1_good"],
    }
    riot_service.match_details_by_id = {
        "EUW1_bad": {"metadata": {"matchId": "EUW1_bad"}},
        "EUW1_good": match_payload("EUW1_good"),
    }

    response = test_client.post("/api/matches/sync")

    assert response.json()["matches_imported"] == 1
    assert response.json()["skipped_reasons"] == {"malformed_match": 1}
    assert test_client.get("/api/matches").json()["items"][0]["riot_match_id"] == "EUW1_good"


def test_sync_rolls_back_partial_match_on_participant_conflict(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    configure_match(
        riot_service,
        payload=match_payload(
            "EUW1_duplicate",
            participants=[
                participant_payload("friend-puuid-1", damage=10000),
                participant_payload("friend-puuid-1", damage=9000),
                participant_payload("friend-puuid-2", damage=11000),
            ],
        ),
        match_id="EUW1_duplicate",
    )

    response = test_client.post("/api/matches/sync")

    assert response.json()["matches_imported"] == 0
    assert response.json()["skipped_reasons"] == {"database_conflict": 1}
    assert test_client.get("/api/matches").json()["items"] == []
    with session_factory() as db:
        assert db.scalar(select(Match).where(Match.riot_match_id == "EUW1_duplicate")) is None


def test_friend_deletion_preserves_historical_match_snapshots(client) -> None:
    test_client, riot_service, session_factory = client
    first_friend, _ = add_default_friends(session_factory)
    configure_match(riot_service)
    test_client.post("/api/matches/sync")
    match_id = test_client.get("/api/matches").json()["items"][0]["id"]

    delete_response = test_client.delete(f"/api/friends/{first_friend.id}")
    detail_response = test_client.get(f"/api/matches/{match_id}").json()

    assert delete_response.status_code == 200
    mohamed = next(
        participant
        for participant in detail_response["participants"]
        if participant["display_name"] == "Mohamed"
    )
    assert mohamed["friend_id"] is None
    assert mohamed["game_name"] == "Windshitter"
    assert test_client.get("/api/friends").json()[0]["display_name"] == "Ahmed"


def test_riot_rate_limit_from_sync_returns_retry_header(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    riot_service.match_ids_by_puuid = {
        "friend-puuid-1": ["EUW1_123"],
    }
    riot_service.match_details_by_id = {
        "EUW1_123": RiotApiError(
            429,
            "Riot API rate limit reached. Try again later. Riot asked clients to retry after 7 seconds.",
            retry_after_seconds=7,
        ),
    }

    response = test_client.post("/api/matches/sync")

    assert response.status_code == 429
    assert response.headers["retry-after"] == "7"


def test_sync_with_missing_api_key_returns_clear_error(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    riot_service.match_ids_error = RiotApiError(503, "Riot API key is not configured.")

    response = test_client.post("/api/matches/sync")

    assert response.status_code == 503
    assert response.json() == {"detail": "Riot API key is not configured."}


def test_stored_match_timestamps_are_based_on_riot_end_time(client) -> None:
    test_client, riot_service, session_factory = client
    add_default_friends(session_factory)
    configure_match(riot_service)

    test_client.post("/api/matches/sync")

    game_end_time = test_client.get("/api/matches").json()["items"][0]["game_end_time"]
    expected = datetime.fromtimestamp(
        (1_784_385_000_000 + (1200 * 1000)) / 1000,
        tz=timezone.utc,
    ).isoformat().replace("+00:00", "Z")
    assert game_end_time == expected
