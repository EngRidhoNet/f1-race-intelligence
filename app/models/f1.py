from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.telemetry import Lap, Stint, TelemetryFrame, TrackShapePoint


class Season(Base, TimestampMixin):
    """F1 season (e.g., 2024)."""

    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)

    # Relationships
    races: Mapped[list["Race"]] = relationship(
        "Race",
        back_populates="season",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Season(year={self.year})>"


class Race(Base, TimestampMixin):
    """Single Grand Prix event within a season."""

    __tablename__ = "races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id"),
        nullable=False,
        index=True,
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    circuit_name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_laps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    season: Mapped["Season"] = relationship("Season", back_populates="races")
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="race",
        cascade="all, delete-orphan",
    )
    track_shape_points: Mapped[list["TrackShapePoint"]] = relationship(
        "TrackShapePoint",
        back_populates="race",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("season_id", "round", name="uq_season_round"),
        Index("ix_races_season_id", "season_id"),
        Index("ix_races_season_round", "season_id", "round"),
    )

    def __repr__(self) -> str:
        return f"<Race(season={self.season_id}, round={self.round}, name={self.name!r})>"


class Session(Base, TimestampMixin):
    """Session inside a race (RACE, QUALI, FP1, etc.)."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(
        ForeignKey("races.id"),
        nullable=False,
        index=True,
    )
    session_type: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fastf1_identifier: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    race: Mapped["Race"] = relationship("Race", back_populates="sessions")
    results: Mapped[list["DriverSessionResult"]] = relationship(
        "DriverSessionResult",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    laps: Mapped[list["Lap"]] = relationship(
        "Lap",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    stints: Mapped[list["Stint"]] = relationship(
        "Stint",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    telemetry_frames: Mapped[list["TelemetryFrame"]] = relationship(
        "TelemetryFrame",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("race_id", "session_type", name="uq_race_session_type"),
        Index("ix_sessions_race_id", "race_id"),
        Index("ix_sessions_race_type", "race_id", "session_type"),
    )

    def __repr__(self) -> str:
        return f"<Session(race_id={self.race_id}, type={self.session_type})>"


class Team(Base, TimestampMixin):
    """Team / constructor."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    short_name: Mapped[str] = mapped_column(String(50), nullable=False)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)

    # Relationships
    results: Mapped[list["DriverSessionResult"]] = relationship(
        "DriverSessionResult",
        back_populates="team",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_teams_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Team(name={self.name!r})>"


class Driver(Base, TimestampMixin):
    """Driver (e.g., Max Verstappen, Charles Leclerc)."""

    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    permanent_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    results: Mapped[list["DriverSessionResult"]] = relationship(
        "DriverSessionResult",
        back_populates="driver",
        cascade="all, delete-orphan",
    )
    laps: Mapped[list["Lap"]] = relationship(
        "Lap",
        back_populates="driver",
        cascade="all, delete-orphan",
    )
    stints: Mapped[list["Stint"]] = relationship(
        "Stint",
        back_populates="driver",
        cascade="all, delete-orphan",
    )
    telemetry_frames: Mapped[list["TelemetryFrame"]] = relationship(
        "TelemetryFrame",
        back_populates="driver",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_drivers_code", "code"),
    )

    def __repr__(self) -> str:
        return f"<Driver(code={self.code!r}, name={self.full_name!r})>"


class DriverSessionResult(Base, TimestampMixin):
    """Classification/result of a driver in a given session (usually Race)."""

    __tablename__ = "driver_session_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.id"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        nullable=False,
        index=True,
    )
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grid_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_status: Mapped[str] = mapped_column(String(50), nullable=False)
    total_race_time_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_text: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gap_to_winner_text: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="results")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="results")
    team: Mapped["Team"] = relationship("Team", back_populates="results")

    __table_args__ = (
        UniqueConstraint("session_id", "driver_id", name="uq_session_driver"),
        Index("ix_results_session_id", "session_id"),
        Index("ix_results_driver_id", "driver_id"),
        Index("ix_results_team_id", "team_id"),
        Index("ix_results_session_driver", "session_id", "driver_id"),
        Index("ix_results_position", "session_id", "position"),
    )

    def __repr__(self) -> str:
        return (
            f"<DriverSessionResult(session_id={self.session_id}, "
            f"driver_id={self.driver_id}, position={self.position})>"
        )
