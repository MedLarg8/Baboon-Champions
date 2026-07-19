from pathlib import Path


def test_production_code_does_not_define_static_friend_lists() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    production_paths = [
        *backend_root.joinpath("app").rglob("*.py"),
        backend_root / ".env.example",
    ]
    forbidden_tokens = [
        "FRIEND_PUUIDS",
        "FRIENDS =",
        "TRACKED_PLAYERS",
        "PLAYER_ACCOUNTS",
    ]

    matches: list[str] = []
    for path in production_paths:
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                matches.append(f"{path.relative_to(backend_root)} contains {token}")

    assert matches == []
