"""
Common F1 database query functions.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.f1 import Season, Race, Session as SessionModel, Driver, Team, DriverSessionResult
from app.models.telemetry import Lap, Stint, TelemetryFrame, TrackShapePoint
from app.core.exceptions import RaceNotFoundException, SessionNotFoundException, DriverNotFoundException


def get_race_by_id(db: Session, race_id: int) -> Race:
    """Get race by ID."""
    race = db.get(Race, race_id)
    if not race:
        raise RaceNotFoundException(f"Race {race_id} not found")
    return race


def get_race_main_session(db: Session, race_id: int) -> SessionModel:
    """Get the main race session for a race."""
    stmt = (
        select(SessionModel)
        .where(SessionModel.race_id == race_id)
        .where(SessionModel.session_type == "RACE")
    )
    session = db.execute(stmt).scalar_one_or_none()
    if not session:
        raise SessionNotFoundException(f"No race session found for race {race_id}")
    return session


def get_driver_by_code(db: Session, code: str) -> Driver:
    """Get driver by code."""
    stmt = select(Driver).where(Driver.code == code.upper())
    driver = db.execute(stmt).scalar_one_or_none()
    if not driver:
        raise DriverNotFoundException(f"Driver {code} not found")
    return driver


def get_race_results(db: Session, session_id: int) -> list[DriverSessionResult]:
    """Get race results ordered by position."""
    stmt = (
        select(DriverSessionResult)
        .where(DriverSessionResult.session_id == session_id)
        .order_by(DriverSessionResult.position.nulls_last())
    )
    return list(db.execute(stmt).scalars().all())


def get_driver_laps(
    db: Session, 
    session_id: int, 
    driver_id: int, 
    lap_range: tuple[int, int] | None = None
) -> list[Lap]:
    """Get laps for a driver in a session, optionally filtered by lap range."""
    stmt = (
        select(Lap)
        .where(Lap.session_id == session_id)
        .where(Lap.driver_id == driver_id)
    )
    
    if lap_range:
        start_lap, end_lap = lap_range
        stmt = stmt.where(Lap.lap_number >= start_lap).where(Lap.lap_number <= end_lap)
    
    stmt = stmt.order_by(Lap.lap_number)
    return list(db.execute(stmt).scalars().all())


def get_driver_stints(db: Session, session_id: int, driver_id: int) -> list[Stint]:
    """Get stints for a driver in a session."""
    stmt = (
        select(Stint)
        .where(Stint.session_id == session_id)
        .where(Stint.driver_id == driver_id)
        .order_by(Stint.stint_number)
    )
    return list(db.execute(stmt).scalars().all())


def get_all_session_stints(db: Session, session_id: int) -> list[Stint]:
    """Get all stints in a session."""
    stmt = (
        select(Stint)
        .where(Stint.session_id == session_id)
        .order_by(Stint.driver_id, Stint.stint_number)
    )
    return list(db.execute(stmt).scalars().all())


def get_track_shape(db: Session, race_id: int) -> list[TrackShapePoint]:
    """Get track shape points for a race."""
    stmt = (
        select(TrackShapePoint)
        .where(TrackShapePoint.race_id == race_id)
        .order_by(TrackShapePoint.order_index)
    )
    return list(db.execute(stmt).scalars().all())


def get_telemetry_frames(
    db: Session, 
    session_id: int, 
    driver_ids: list[int] | None = None
) -> list[TelemetryFrame]:
    """Get telemetry frames for a session, optionally filtered by drivers."""
    stmt = (
        select(TelemetryFrame)
        .where(TelemetryFrame.session_id == session_id)
    )
    
    if driver_ids:
        stmt = stmt.where(TelemetryFrame.driver_id.in_(driver_ids))
    
    stmt = stmt.order_by(TelemetryFrame.t_rel_sec, TelemetryFrame.driver_id)
    return list(db.execute(stmt).scalars().all())


def count_pit_stops(db: Session, session_id: int, driver_id: int) -> int:
    """Count pit stops for a driver in a session."""
    stmt = (
        select(func.count())
        .select_from(Lap)
        .where(Lap.session_id == session_id)
        .where(Lap.driver_id == driver_id)
        .where(Lap.is_pit_lap == True)
    )
    return db.execute(stmt).scalar() or 0


def get_lap_statistics(
    db: Session, 
    session_id: int, 
    driver_id: int, 
    lap_range: tuple[int, int] | None = None
) -> dict:
    """
    Get aggregated lap statistics for a driver.
    
    Returns dict with:
        - avg_lap_time: Average lap time in seconds
        - min_lap_time: Fastest lap time
        - max_lap_time: Slowest lap time
        - total_laps: Number of laps
    """
    stmt = (
        select(
            func.avg(Lap.lap_time_sec).label("avg_lap_time"),
            func.min(Lap.lap_time_sec).label("min_lap_time"),
            func.max(Lap.lap_time_sec).label("max_lap_time"),
            func.count().label("total_laps")
        )
        .where(Lap.session_id == session_id)
        .where(Lap.driver_id == driver_id)
        .where(Lap.lap_time_sec != None)
        .where(Lap.is_pit_lap == False)  # Exclude pit laps
    )
    
    if lap_range:
        start_lap, end_lap = lap_range
        stmt = stmt.where(Lap.lap_number >= start_lap).where(Lap.lap_number <= end_lap)
    
    result = db.execute(stmt).one()
    
    return {
        "avg_lap_time": float(result.avg_lap_time) if result.avg_lap_time else None,
        "min_lap_time": float(result.min_lap_time) if result.min_lap_time else None,
        "max_lap_time": float(result.max_lap_time) if result.max_lap_time else None,
        "total_laps": int(result.total_laps) if result.total_laps else 0
    }