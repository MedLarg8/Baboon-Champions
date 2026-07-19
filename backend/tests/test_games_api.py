from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_riot_account_service
from app.database.session import Base, create_database_engine, get_db
from app.main import create_app
from app.models.friend import Friend
from app.models.game import Game, GameParticipant
from app.schemas.game import GameCreate
from app.services.friends import normalize_riot_part
from app.services.games import GameValidationError, create_game
from app.services.riot import RiotAccount


class FakeRiotService:
    async def resolve_account_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
    ) -> RiotAccount:
        return RiotAccount(
            puuid=f"{game_name}-{tag_line}-puuid",
            game_name=game_name,
            tag_line=tag_line,
        )


@pytest.fixture()
def client(tmp_path) -> Generator[
    tuple[TestClient, sessionmaker[Session]],
    None,
    None,
]:
    app = create_app(initialize_database=False)
    db_path = tmp_path / "games.db"
    engine = create_database_engine(
        f"sqlite:///{db_path.as_posix()}",
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_riot_account_service] = lambda: FakeRiotService()

    with TestClient(app) as test_client:
        yield test_client, testing_session_local

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


def add_default_friends(session_factory: sessionmaker[Session]) -> tuple[Friend, Friend, Friend]:
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
        add_friend(
            session_factory,
            display_name="Youssef",
            game_name="Fire",
            tag_line="EUW",
            puuid="friend-puuid-3",
        ),
    )


def game_payload(first_friend_id: int, second_friend_id: int, third_friend_id: int | None = None) -> dict:
    participants = [
        {
            "friend_id": first_friend_id,
            "champion_name": "Yone",
            "damage_to_champions": 31400,
        },
        {
            "friend_id": second_friend_id,
            "champion_name": "Malphite",
            "damage_to_champions": 12300,
        },
    ]
    if third_friend_id is not None:
        participants.append(
            {
                "friend_id": third_friend_id,
                "champion_name": "Brand",
                "damage_to_champions": 48500,
            },
        )
    return {
        "played_at": "2026-07-19T21:30:00Z",
        "participants": participants,
    }


def create_default_game(test_client: TestClient, friends: tuple[Friend, Friend, Friend]) -> dict:
    response = test_client.post(
        "/api/games",
        json=game_payload(friends[0].id, friends[1].id, friends[2].id),
    )
    assert response.status_code == 201
    return response.json()


def test_create_valid_game_calculates_baboon(client) -> None:
    test_client, session_factory = client
    friends = add_default_friends(session_factory)

    response = test_client.post(
        "/api/games",
        json=game_payload(friends[0].id, friends[1].id, friends[2].id),
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["player_count"] == 3
    assert payload["lowest_damage_to_champions"] == 12300
    assert payload["baboons"][0]["display_name"] == "Ahmed"
    assert payload["baboons"][0]["champion_name"] == "Malphite"
    assert [participant["damage_to_champions"] for participant in payload["participants"]] == [
        48500,
        31400,
        12300,
    ]


def test_create_game_requires_at_least_two_players(client) -> None:
    test_client, session_factory = client
    friend = add_default_friends(session_factory)[0]

    response = test_client.post(
        "/api/games",
        json={
            "played_at": "2026-07-19T21:30:00Z",
            "participants": [
                {
                    "friend_id": friend.id,
                    "champion_name": "Yone",
                    "damage_to_champions": 31400,
                },
            ],
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "At least two players must be selected."}


def test_create_game_rejects_duplicate_friends(client) -> None:
    test_client, session_factory = client
    friend = add_default_friends(session_factory)[0]

    response = test_client.post(
        "/api/games",
        json=game_payload(friend.id, friend.id),
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Players cannot appear twice in the same game."}
    assert test_client.get("/api/games").json()["items"] == []


def test_create_game_rejects_duplicate_champions(client) -> None:
    test_client, session_factory = client
    first_friend, second_friend, _ = add_default_friends(session_factory)

    response = test_client.post(
        "/api/games",
        json={
            "played_at": "2026-07-19T21:30:00Z",
            "participants": [
                {
                    "friend_id": first_friend.id,
                    "champion_name": " Yone ",
                    "damage_to_champions": 31400,
                },
                {
                    "friend_id": second_friend.id,
                    "champion_name": "yone",
                    "damage_to_champions": 12300,
                },
            ],
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Champions cannot be picked twice in the same game."}
    assert test_client.get("/api/games").json()["items"] == []


def test_create_game_rejects_missing_friend(client) -> None:
    test_client, session_factory = client
    friend = add_default_friends(session_factory)[0]

    response = test_client.post(
        "/api/games",
        json=game_payload(friend.id, 999),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "One or more selected friends do not exist."}


def test_create_game_rejects_missing_champion(client) -> None:
    test_client, session_factory = client
    first_friend, second_friend, _ = add_default_friends(session_factory)

    response = test_client.post(
        "/api/games",
        json={
            "played_at": "2026-07-19T21:30:00Z",
            "participants": [
                {
                    "friend_id": first_friend.id,
                    "champion_name": " ",
                    "damage_to_champions": 31400,
                },
                {
                    "friend_id": second_friend.id,
                    "champion_name": "Malphite",
                    "damage_to_champions": 12300,
                },
            ],
        },
    )

    assert response.status_code == 422
    assert "champion name cannot be empty" in response.text


def test_create_game_rejects_negative_damage(client) -> None:
    test_client, session_factory = client
    first_friend, second_friend, _ = add_default_friends(session_factory)

    response = test_client.post(
        "/api/games",
        json={
            "played_at": "2026-07-19T21:30:00Z",
            "participants": [
                {
                    "friend_id": first_friend.id,
                    "champion_name": "Yone",
                    "damage_to_champions": -1,
                },
                {
                    "friend_id": second_friend.id,
                    "champion_name": "Malphite",
                    "damage_to_champions": 12300,
                },
            ],
        },
    )

    assert response.status_code == 422


def test_create_game_marks_tied_co_baboons(client) -> None:
    test_client, session_factory = client
    first_friend, second_friend, third_friend = add_default_friends(session_factory)

    response = test_client.post(
        "/api/games",
        json={
            "played_at": "2026-07-19T21:30:00Z",
            "participants": [
                {
                    "friend_id": first_friend.id,
                    "champion_name": "Yone",
                    "damage_to_champions": 12300,
                },
                {
                    "friend_id": second_friend.id,
                    "champion_name": "Malphite",
                    "damage_to_champions": 12300,
                },
                {
                    "friend_id": third_friend.id,
                    "champion_name": "Brand",
                    "damage_to_champions": 48500,
                },
            ],
        },
    )

    assert response.status_code == 201
    assert {baboon["display_name"] for baboon in response.json()["baboons"]} == {
        "Mohamed",
        "Ahmed",
    }


def test_create_game_ignores_submitted_baboon_values(client) -> None:
    test_client, session_factory = client
    first_friend, second_friend, _ = add_default_friends(session_factory)

    response = test_client.post(
        "/api/games",
        json={
            "played_at": "2026-07-19T21:30:00Z",
            "participants": [
                {
                    "friend_id": first_friend.id,
                    "champion_name": "Yone",
                    "damage_to_champions": 99999,
                    "is_baboon": True,
                },
                {
                    "friend_id": second_friend.id,
                    "champion_name": "Malphite",
                    "damage_to_champions": 1,
                    "is_baboon": False,
                },
            ],
        },
    )

    assert response.status_code == 201
    baboons = response.json()["baboons"]
    assert len(baboons) == 1
    assert baboons[0]["display_name"] == "Ahmed"


def test_game_persistence_rolls_back_atomically_on_database_error(client, monkeypatch) -> None:
    _, session_factory = client
    first_friend, second_friend, _ = add_default_friends(session_factory)

    with session_factory() as db:
        payload = GameCreate.model_validate(game_payload(first_friend.id, second_friend.id))

        def broken_commit() -> None:
            raise IntegrityError("insert", {}, Exception("database failed"))

        monkeypatch.setattr(db, "commit", broken_commit)

        with pytest.raises(GameValidationError):
            create_game(db, payload)

        assert db.scalar(select(func.count()).select_from(Game)) == 0
        assert db.scalar(select(func.count()).select_from(GameParticipant)) == 0


def test_list_games_newest_first_with_pagination(client) -> None:
    test_client, session_factory = client
    first_friend, second_friend, _ = add_default_friends(session_factory)
    played_dates = [
        "2026-07-19T21:30:00Z",
        "2026-07-21T21:30:00Z",
        "2026-07-20T21:30:00Z",
    ]
    for played_at in played_dates:
        payload = game_payload(first_friend.id, second_friend.id)
        payload["played_at"] = played_at
        test_client.post("/api/games", json=payload)

    response = test_client.get("/api/games?limit=2&offset=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 2
    assert payload["offset"] == 0
    assert payload["total"] == 3
    assert [item["played_at"] for item in payload["items"]] == [
        "2026-07-21T21:30:00Z",
        "2026-07-20T21:30:00Z",
    ]


def test_game_detail_and_missing_game(client) -> None:
    test_client, session_factory = client
    friends = add_default_friends(session_factory)
    game = create_default_game(test_client, friends)

    detail_response = test_client.get(f"/api/games/{game['id']}")
    missing_response = test_client.get("/api/games/999")

    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == game["id"]
    assert [participant["damage_to_champions"] for participant in detail_response.json()["participants"]] == [
        48500,
        31400,
        12300,
    ]
    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Game not found."}


def test_current_baboon_empty_before_history_exists(client) -> None:
    test_client, _ = client

    response = test_client.get("/api/baboon/current")

    assert response.status_code == 200
    assert response.json() == {
        "has_current_baboon": False,
        "game": None,
        "baboons": [],
    }


def test_current_baboon_after_one_game(client) -> None:
    test_client, session_factory = client
    friends = add_default_friends(session_factory)
    create_default_game(test_client, friends)

    response = test_client.get("/api/baboon/current")

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_current_baboon"] is True
    assert payload["game"]["played_at"] == "2026-07-19T21:30:00Z"
    assert payload["baboons"][0]["display_name"] == "Ahmed"
    assert payload["baboons"][0]["damage_to_champions"] == 12300


def test_current_baboon_after_multiple_games_uses_newest_played_at(client) -> None:
    test_client, session_factory = client
    first_friend, second_friend, _ = add_default_friends(session_factory)

    old_payload = game_payload(first_friend.id, second_friend.id)
    old_payload["played_at"] = "2026-07-19T21:30:00Z"
    new_payload = game_payload(first_friend.id, second_friend.id)
    new_payload["played_at"] = "2026-07-20T21:30:00Z"
    new_payload["participants"][0]["damage_to_champions"] = 1
    new_payload["participants"][1]["damage_to_champions"] = 20000
    test_client.post("/api/games", json=old_payload)
    test_client.post("/api/games", json=new_payload)

    response = test_client.get("/api/baboon/current")

    assert response.json()["baboons"][0]["display_name"] == "Mohamed"


def test_deleting_newest_game_restores_previous_baboon(client) -> None:
    test_client, session_factory = client
    first_friend, second_friend, _ = add_default_friends(session_factory)

    old_payload = game_payload(first_friend.id, second_friend.id)
    old_payload["played_at"] = "2026-07-19T21:30:00Z"
    new_payload = game_payload(first_friend.id, second_friend.id)
    new_payload["played_at"] = "2026-07-20T21:30:00Z"
    new_payload["participants"][0]["damage_to_champions"] = 1
    new_payload["participants"][1]["damage_to_champions"] = 20000
    test_client.post("/api/games", json=old_payload)
    newest = test_client.post("/api/games", json=new_payload).json()

    delete_response = test_client.delete(f"/api/games/{newest['id']}")
    current_response = test_client.get("/api/baboon/current")

    assert delete_response.status_code == 200
    assert delete_response.json() == {"detail": "Game deleted."}
    assert current_response.json()["baboons"][0]["display_name"] == "Ahmed"


def test_deleting_game_cascades_participants(client) -> None:
    test_client, session_factory = client
    friends = add_default_friends(session_factory)
    game = create_default_game(test_client, friends)

    response = test_client.delete(f"/api/games/{game['id']}")

    assert response.status_code == 200
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Game)) == 0
        assert db.scalar(select(func.count()).select_from(GameParticipant)) == 0


def test_friend_deletion_preserves_historical_game_participants(client) -> None:
    test_client, session_factory = client
    friends = add_default_friends(session_factory)
    game = create_default_game(test_client, friends)

    delete_response = test_client.delete(f"/api/friends/{friends[0].id}")
    detail_response = test_client.get(f"/api/games/{game['id']}")

    assert delete_response.status_code == 200
    mohamed = next(
        participant
        for participant in detail_response.json()["participants"]
        if participant["display_name"] == "Mohamed"
    )
    assert mohamed["friend_id"] is None
    assert mohamed["game_name"] == "Windshitter"
    assert test_client.get("/api/friends").json()[0]["display_name"] == "Ahmed"
