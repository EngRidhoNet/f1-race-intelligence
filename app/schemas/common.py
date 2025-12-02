# app/schemas/common.py
"""Common response schemas."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""
    status: str


# app/schemas/f1.py
"""F1-related schemas."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SeasonSchema(BaseModel):
    """Season response schema."""
    year: int
    race_count: int
    
    model_config = ConfigDict(from_attributes=True)


class RaceListSchema(BaseModel):
    """Race list item schema."""
    id: int
    round: int
    name: str
    circuit_name: str
    country: str
    date: datetime
    total_laps: int | None
    
    model_config = ConfigDict(from_attributes=True)


class DriverSchema(BaseModel):
    """Driver schema."""
    id: int
    code: str
    full_name: str
    country: str | None
    
    model_config = ConfigDict(from_attributes=True)


class TeamSchema(BaseModel):
    """Team schema."""
    id: int
    name: str
    short_name: str
    color_hex: str | None
    
    model_config = ConfigDict(from_attributes=True)


class DriverWithTeamSchema(BaseModel):
    """Driver with team information."""
    id: int
    code: str
    full_name: str
    team: str
    
    model_config = ConfigDict(from_attributes=True)


class RaceDetailSchema(BaseModel):
    """Detailed race information."""
    id: int
    season_year: int
    round: int
    name: str
    circuit_name: str
    country: str
    date: datetime
    total_laps: int | None
    main_session_id: int | None
    
    model_config = ConfigDict(from_attributes=True)


class WinnerSchema(BaseModel):
    """Race winner schema."""
    driver_code: str
    driver_name: str
    team: str


class PodiumDriverSchema(BaseModel):
    """Podium driver schema."""
    position: int
    driver_code: str
    driver_name: str
    team: str


class RaceSummarySchema(BaseModel):
    """High-level race summary."""
    race_id: int
    race_name: str
    winner: WinnerSchema | None
    podium: list[PodiumDriverSchema]
    total_laps: int
    total_drivers: int
    finished_drivers: int
    dnf_count: int
    
    model_config = ConfigDict(from_attributes=True)


class ResultSchema(BaseModel):
    """Driver session result schema."""
    position: int | None
    driver_code: str
    driver_name: str
    team: str
    points: float | None
    time_text: str | None
    gap_to_winner_text: str | None
    final_status: str
    grid_position: int | None
    
    model_config = ConfigDict(from_attributes=True)