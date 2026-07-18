from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Friend(Base):
    __tablename__ = "friends"
    __table_args__ = (
        UniqueConstraint(
            "normalized_game_name",
            "normalized_tag_line",
            name="uq_friends_normalized_riot_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    game_name: Mapped[str] = mapped_column(String(120), nullable=False)
    tag_line: Mapped[str] = mapped_column(String(40), nullable=False)
    normalized_game_name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_tag_line: Mapped[str] = mapped_column(String(40), nullable=False)
    puuid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
