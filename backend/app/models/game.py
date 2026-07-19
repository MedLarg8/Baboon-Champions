from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.friend import utc_now


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
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

    participants: Mapped[list[GameParticipant]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="desc(GameParticipant.damage_to_champions)",
    )


class GameParticipant(Base):
    __tablename__ = "game_participants"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "friend_id",
            name="uq_game_participants_game_friend",
        ),
        CheckConstraint("damage_to_champions >= 0", name="ck_game_participants_damage_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    friend_id: Mapped[int | None] = mapped_column(
        ForeignKey("friends.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    display_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    game_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    tag_line_snapshot: Mapped[str] = mapped_column(String(40), nullable=False)
    champion_name: Mapped[str] = mapped_column(String(80), nullable=False)
    damage_to_champions: Mapped[int] = mapped_column(Integer, nullable=False)
    is_baboon: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    game: Mapped[Game] = relationship(back_populates="participants")
