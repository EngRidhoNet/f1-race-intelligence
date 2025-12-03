# app/schemas/f1.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


# === Seasons ===

class SeasonSchema(BaseModel):
    year: int
    race_count: int  # ini di-annotate dari query aggregate

    # kalau suatu saat kamu pakai model_validate untuk Season
    model_config = ConfigDict(from_attributes=True)


# === Races list ===

class RaceListSchema(BaseModel):
    id: int
    season_id: int
    round: int
    name: str
    circuit_name: str
    country: str
    date: datetime
    total_laps: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# === Race detail ===

class RaceDetailSchema(BaseModel):
    id: int
    season_year: int
    round: int
    name: str
    circuit_name: str
    country: str
    date: datetime
    total_laps: int | None
    main_session_id: int | None


# === Winner / Podium helper schemas ===

class WinnerSchema(BaseModel):
    driver_code: str
    driver_name: str
    team: str  # short_name


class PodiumDriverSchema(BaseModel):
    position: int
    driver_code: str
    driver_name: str
    team: str  # short_name


# === Race summary ===

class RaceSummarySchema(BaseModel):
    race_id: int
    race_name: str
    winner: Optional[WinnerSchema] = None
    podium: List[PodiumDriverSchema] = []
    total_laps: int
    total_drivers: int
    finished_drivers: int
    dnf_count: int


# === Results & drivers ===

class ResultSchema(BaseModel):
    position: Optional[int]
    driver_code: str
    driver_name: str
    team: str  # short_name
    points: Optional[float]
    time_text: Optional[str]
    gap_to_winner_text: Optional[str]
    final_status: str
    grid_position: Optional[int]


class DriverWithTeamSchema(BaseModel):
    id: int
    code: str
    full_name: str
    team: str  # short_name
