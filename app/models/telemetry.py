from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.f1 import Session, Driver, Race


class Lap(Base, TimestampMixin):
    """Individual lap data for a driver."""
    
    __tablename__ = "laps"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lap_time_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector1_time_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector2_time_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    sector3_time_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_pit_lap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tyre_compound: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "SOFT", "MEDIUM", "HARD"
    tyre_life_laps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    track_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "1" (green), "2" (yellow), etc.
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="laps")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="laps")
    
    __table_args__ = (
        Index("ix_laps_session_driver_lap", "session_id", "driver_id", "lap_number", unique=True),
        Index("ix_laps_session_lap", "session_id", "lap_number"),
    )
    
    def __repr__(self) -> str:
        return f"<Lap(session_id={self.session_id}, driver_id={self.driver_id}, lap={self.lap_number})>"


class Stint(Base, TimestampMixin):
    """Tyre stint for a driver."""
    
    __tablename__ = "stints"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    stint_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_lap: Mapped[int] = mapped_column(Integer, nullable=False)
    end_lap: Mapped[int] = mapped_column(Integer, nullable=False)
    compound: Mapped[str] = mapped_column(String(20), nullable=False)  # "SOFT", "MEDIUM", "HARD"
    avg_lap_time_sec: Mapped[float] = mapped_column(Float, nullable=False)
    laps_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="stints")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="stints")
    
    __table_args__ = (
        Index("ix_stints_session_driver_stint", "session_id", "driver_id", "stint_number", unique=True),
        Index("ix_stints_session_driver", "session_id", "driver_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Stint(session_id={self.session_id}, driver_id={self.driver_id}, stint={self.stint_number}, compound={self.compound})>"


class TelemetryFrame(Base):
    """Single telemetry data point for a driver."""
    
    __tablename__ = "telemetry_frames"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    t_rel_sec: Mapped[float] = mapped_column(Float, nullable=False)  # Time since session start
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    x_norm: Mapped[float] = mapped_column(Float, nullable=False)  # Normalized 0..1
    y_norm: Mapped[float] = mapped_column(Float, nullable=False)  # Normalized 0..1
    speed_kph: Mapped[float | None] = mapped_column(Float, nullable=True)
    throttle: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0..1
    brake: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0..1
    gear: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="telemetry_frames")
    driver: Mapped["Driver"] = relationship("Driver", back_populates="telemetry_frames")
    
    __table_args__ = (
        Index("ix_telemetry_session_driver_time", "session_id", "driver_id", "t_rel_sec"),
        Index("ix_telemetry_session_time", "session_id", "t_rel_sec"),
    )
    
    def __repr__(self) -> str:
        return f"<TelemetryFrame(session_id={self.session_id}, driver_id={self.driver_id}, t={self.t_rel_sec:.2f})>"


class TrackShapePoint(Base):
    """Track shape polyline point."""
    
    __tablename__ = "track_shape_points"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    x_norm: Mapped[float] = mapped_column(Float, nullable=False)  # Normalized 0..1
    y_norm: Mapped[float] = mapped_column(Float, nullable=False)  # Normalized 0..1
    
    # Relationships
    race: Mapped["Race"] = relationship("Race", back_populates="track_shape_points")
    
    __table_args__ = (
        Index("ix_track_shape_race_order", "race_id", "order_index", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<TrackShapePoint(race_id={self.race_id}, order={self.order_index})>"