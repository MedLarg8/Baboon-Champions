from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_riot_account_service
from app.database.session import Base, get_db
from app.main import create_app
from app.services.riot import RiotAccount, RiotApiError


class FakeRiotService:
    def __init__(
        self,
        account: RiotAccount | None = None,
        error: RiotApiError | None = None,
    ) -> None:
        self.account = account or RiotAccount(
            puuid="puuid-1",
            game_name="Windshitter",
            tag_line="EUW",
        )
        self.error = error

    async def resolve_account_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
    ) -> RiotAccount:
        if self.error is not None:
            raise self.error
        return self.account


@pytest.fixture()
def client(tmp_path) -> Generator[tuple[TestClient, dict[str, FakeRiotService]], None, None]:
    app = create_app(initialize_database=False)
    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    riot_state = {"service": FakeRiotService()}

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    def override_riot_service() -> FakeRiotService:
        return riot_state["service"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_riot_account_service] = override_riot_service

    with TestClient(app) as test_client:
        yield test_client, riot_state

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_health_endpoint(client) -> None:
    test_client, _ = client

    response = test_client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "aram-baboon-backend"}


def test_register_friend_success(client) -> None:
    test_client, _ = client

    response = test_client.post(
        "/api/friends",
        json={
            "display_name": " Mohamed ",
            "game_name": " Windshitter ",
            "tag_line": " EUW ",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["display_name"] == "Mohamed"
    assert payload["game_name"] == "Windshitter"
    assert payload["tag_line"] == "EUW"
    assert payload["puuid"] == "puuid-1"
    assert "created_at" in payload


def test_register_friend_riot_account_not_found(client) -> None:
    test_client, riot_state = client
    riot_state["service"] = FakeRiotService(
        error=RiotApiError(404, "Riot account not found."),
    )

    response = test_client.post(
        "/api/friends",
        json={"display_name": "Mo", "game_name": "Missing", "tag_line": "EUW"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Riot account not found."}


def test_register_friend_invalid_or_expired_api_key(client) -> None:
    test_client, riot_state = client
    riot_state["service"] = FakeRiotService(
        error=RiotApiError(502, "Riot API key is invalid, missing, or expired."),
    )

    response = test_client.post(
        "/api/friends",
        json={"display_name": "Mo", "game_name": "Windshitter", "tag_line": "EUW"},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Riot API key is invalid, missing, or expired."}


def test_duplicate_puuid_registration_returns_conflict(client) -> None:
    test_client, _ = client

    first_response = test_client.post(
        "/api/friends",
        json={"display_name": "Mo", "game_name": "Windshitter", "tag_line": "EUW"},
    )
    second_response = test_client.post(
        "/api/friends",
        json={"display_name": "Other", "game_name": "Windshitter", "tag_line": "EUW"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json() == {"detail": "This Riot account is already registered."}


def test_list_registered_friends(client) -> None:
    test_client, riot_state = client

    test_client.post(
        "/api/friends",
        json={"display_name": "Mo", "game_name": "Windshitter", "tag_line": "EUW"},
    )
    riot_state["service"] = FakeRiotService(
        account=RiotAccount(puuid="puuid-2", game_name="Second", tag_line="EUW"),
    )
    test_client.post(
        "/api/friends",
        json={"display_name": "Sami", "game_name": "Second", "tag_line": "EUW"},
    )

    response = test_client.get("/api/friends")

    assert response.status_code == 200
    payload = response.json()
    assert [friend["display_name"] for friend in payload] == ["Mo", "Sami"]


def test_delete_friend(client) -> None:
    test_client, _ = client
    create_response = test_client.post(
        "/api/friends",
        json={"display_name": "Mo", "game_name": "Windshitter", "tag_line": "EUW"},
    )
    friend_id = create_response.json()["id"]

    delete_response = test_client.delete(f"/api/friends/{friend_id}")
    list_response = test_client.get("/api/friends")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"detail": "Friend deleted."}
    assert list_response.json() == []


def test_delete_nonexistent_friend(client) -> None:
    test_client, _ = client

    response = test_client.delete("/api/friends/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Friend not found."}


@pytest.mark.parametrize(
    "payload",
    [
        {"display_name": "", "game_name": "Windshitter", "tag_line": "EUW"},
        {"display_name": "Mo", "game_name": " ", "tag_line": "EUW"},
        {"display_name": "Mo", "game_name": "Windshitter", "tag_line": ""},
    ],
)
def test_required_field_validation(client, payload) -> None:
    test_client, _ = client

    response = test_client.post("/api/friends", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()
