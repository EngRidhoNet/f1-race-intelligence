# app/schemas/telemetry.py
"""Telemetry-related schemas."""
from pydantic import BaseModel, ConfigDict


class LapSchema(BaseModel):
    """Lap data schema."""
    lap_number: int
    lap_time_sec: float | None
    sector1_time_sec: float | None
    sector2_time_sec: float | None
    sector3_time_sec: float | None
    is_pit_lap: bool
    tyre_compound: str | None
    tyre_life_laps: int | None
    track_status: str | None
    
    model_config = ConfigDict(from_attributes=True)


class StintSchema(BaseModel):
    """Stint data schema."""
    stint_number: int
    start_lap: int
    end_lap: int
    compound: str
    avg_lap_time_sec: float
    laps_count: int
    
    model_config = ConfigDict(from_attributes=True)


class DriverStintsSchema(BaseModel):
    """Driver stints collection."""
    driver_code: str
    driver_name: str
    team: str
    stints: list[StintSchema]


class TrackShapePointSchema(BaseModel):
    """Track shape point schema."""
    order_index: int
    x_norm: float
    y_norm: float
    
    model_config = ConfigDict(from_attributes=True)


class CarPositionSchema(BaseModel):
    """Single car position for WebSocket replay."""
    driver_code: str
    x: float
    y: float
    speed_kph: float | None
    lap: int


class ReplayFrameSchema(BaseModel):
    """WebSocket replay frame."""
    t: float  # Time in seconds
    cars: list[CarPositionSchema]