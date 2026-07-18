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


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    riot_match_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    queue_id: Mapped[int] = mapped_column(Integer, nullable=False)
    game_creation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    game_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    game_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    game_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    participants: Mapped[list[MatchParticipant]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
        order_by="desc(MatchParticipant.damage_to_champions)",
    )


class MatchParticipant(Base):
    __tablename__ = "match_participants"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "puuid_snapshot",
            name="uq_match_participants_match_puuid",
        ),
        CheckConstraint("damage_to_champions >= 0", name="ck_match_participants_damage_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    friend_id: Mapped[int | None] = mapped_column(
        ForeignKey("friends.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    puuid_snapshot: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    game_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    tag_line_snapshot: Mapped[str] = mapped_column(String(40), nullable=False)
    champion_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    champion_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kills: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deaths: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    damage_to_champions: Mapped[int] = mapped_column(Integer, nullable=False)
    win: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_baboon: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    match: Mapped[Match] = relationship(back_populates="participants")
