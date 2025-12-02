"""Telemetry endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db_session
from app.core.exceptions import race_not_found, driver_not_found
from app.schemas.telemetry import (
    StintSchema,
    DriverStintsSchema,
    LapSchema,
    TrackShapePointSchema
)
from app.services import f1_queries

router = APIRouter(prefix="/races", tags=["Telemetry"])


@router.get("/{race_id}/stints", response_model=list[DriverStintsSchema])
async def get_stints(
    race_id: int,
    driver_code: str | None = Query(None, description="Filter by driver code"),
    db: Session = Depends(get_db_session)
) -> list[DriverStintsSchema]:
    """Get stint data for a race, optionally filtered by driver."""
    try:
        session = f1_queries.get_race_main_session(db, race_id)
    except:
        raise race_not_found(race_id)
    
    if driver_code:
        # Single driver
        try:
            driver = f1_queries.get_driver_by_code(db, driver_code)
        except:
            raise driver_not_found(driver_code)
        
        stints = f1_queries.get_driver_stints(db, session.id, driver.id)
        
        # Get team info from results
        results = f1_queries.get_race_results(db, session.id)
        driver_result = next((r for r in results if r.driver_id == driver.id), None)
        team_name = driver_result.team.short_name if driver_result else "Unknown"
        
        return [
            DriverStintsSchema(
                driver_code=driver.code,
                driver_name=driver.full_name,
                team=team_name,
                stints=[StintSchema.model_validate(s) for s in stints]
            )
        ]
    else:
        # All drivers
        results = f1_queries.get_race_results(db, session.id)
        all_stints = f1_queries.get_all_session_stints(db, session.id)
        
        # Group stints by driver
        driver_stint_map = {}
        for stint in all_stints:
            if stint.driver_id not in driver_stint_map:
                driver_stint_map[stint.driver_id] = []
            driver_stint_map[stint.driver_id].append(stint)
        
        # Build response
        response = []
        for result in results:
            driver = result.driver
            stints = driver_stint_map.get(driver.id, [])
            
            response.append(
                DriverStintsSchema(
                    driver_code=driver.code,
                    driver_name=driver.full_name,
                    team=result.team.short_name,
                    stints=[StintSchema.model_validate(s) for s in stints]
                )
            )
        
        return response


@router.get("/{race_id}/laps", response_model=list[LapSchema])
async def get_laps(
    race_id: int,
    driver_code: str = Query(..., description="Driver code (required)"),
    lap_start: int | None = Query(None, description="Start lap number"),
    lap_end: int | None = Query(None, description="End lap number"),
    db: Session = Depends(get_db_session)
) -> list[LapSchema]:
    """Get lap data for a specific driver in a race."""
    try:
        session = f1_queries.get_race_main_session(db, race_id)
        driver = f1_queries.get_driver_by_code(db, driver_code)
    except:
        raise race_not_found(race_id)
    
    # Build lap range
    lap_range = None
    if lap_start is not None and lap_end is not None:
        lap_range = (lap_start, lap_end)
    
    laps = f1_queries.get_driver_laps(db, session.id, driver.id, lap_range)
    
    return [LapSchema.model_validate(lap) for lap in laps]


@router.get("/{race_id}/track-shape", response_model=list[TrackShapePointSchema])
async def get_track_shape(
    race_id: int,
    db: Session = Depends(get_db_session)
) -> list[TrackShapePointSchema]:
    """Get track shape polyline for a race."""
    try:
        f1_queries.get_race_by_id(db, race_id)
    except:
        raise race_not_found(race_id)
    
    points = f1_queries.get_track_shape(db, race_id)
    
    return [TrackShapePointSchema.model_validate(p) for p in points]