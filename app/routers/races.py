from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.deps import get_db_session
from app.core.exceptions import race_not_found
from app.models.f1 import Season, Race, Session as SessionModel, DriverSessionResult
from app.schemas.f1 import (
    SeasonSchema,
    RaceListSchema,
    RaceDetailSchema,
    RaceSummarySchema,
    ResultSchema,
    DriverWithTeamSchema,
    WinnerSchema,
    PodiumDriverSchema,
)
from app.services import f1_queries

router = APIRouter(prefix="/seasons", tags=["Races"])


@router.get("", response_model=list[SeasonSchema])
async def list_seasons(db: Session = Depends(get_db_session)) -> list[SeasonSchema]:
    """
    List all seasons with race counts.
    """
    stmt = (
        select(
            Season,
            func.count(Race.id).label("race_count"),
        )
        .outerjoin(Race)
        .group_by(Season.id)
        .order_by(Season.year.desc())
    )

    results = db.execute(stmt).all()

    return [
        SeasonSchema(year=season.year, race_count=race_count)
        for season, race_count in results
    ]


@router.get("/{year}/races", response_model=list[RaceListSchema])
async def list_races(
    year: int,
    db: Session = Depends(get_db_session),
) -> list[RaceListSchema]:
    """
    List all races in a given season (by year).
    """
    stmt = select(Season).where(Season.year == year)
    season = db.execute(stmt).scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail=f"Season {year} not found")

    stmt = (
        select(Race)
        .where(Race.season_id == season.id)
        .order_by(Race.round)
    )
    races = db.execute(stmt).scalars().all()

    return [RaceListSchema.model_validate(race) for race in races]


@router.get("/{race_id}", response_model=RaceDetailSchema)
async def get_race(
    race_id: int,
    db: Session = Depends(get_db_session),
) -> RaceDetailSchema:
    """
    Get detailed information about a race.
    """
    try:
        race = f1_queries.get_race_by_id(db, race_id)
    except Exception:
        raise race_not_found(race_id)

    # Try to get main session (e.g. RACE)
    main_session_id: int | None = None
    try:
        session = f1_queries.get_race_main_session(db, race_id)
        main_session_id = session.id
    except Exception:
        # If main session not found, just leave as None
        pass

    return RaceDetailSchema(
        id=race.id,
        season_year=race.season.year,
        round=race.round,
        name=race.name,
        circuit_name=race.circuit_name,
        country=race.country,
        date=race.date,
        total_laps=race.total_laps,
        main_session_id=main_session_id,
    )


@router.get("/{race_id}/summary", response_model=RaceSummarySchema)
async def get_race_summary(
    race_id: int,
    db: Session = Depends(get_db_session),
) -> RaceSummarySchema:
    """
    Get high-level race summary (winner, podium, counts).
    """
    try:
        race = f1_queries.get_race_by_id(db, race_id)
        session = f1_queries.get_race_main_session(db, race_id)
    except Exception:
        raise race_not_found(race_id)

    # Get classification
    results: list[DriverSessionResult] = f1_queries.get_race_results(db, session.id)

    # Winner
    winner: WinnerSchema | None = None
    if results and results[0].position == 1:
        winner = WinnerSchema(
            driver_code=results[0].driver.code,
            driver_name=results[0].driver.full_name,
            team=results[0].team.short_name,
        )

    # Podium
    podium: list[PodiumDriverSchema] = []
    for result in results[:3]:
        if result.position and result.position <= 3:
            podium.append(
                PodiumDriverSchema(
                    position=result.position,
                    driver_code=result.driver.code,
                    driver_name=result.driver.full_name,
                    team=result.team.short_name,
                )
            )

    # Finishers vs DNF
    finished = sum(1 for r in results if r.final_status == "Finished")
    dnf = sum(
        1
        for r in results
        if "DNF" in r.final_status
        or r.final_status not in ["Finished", "+1 Lap", "+2 Laps"]
    )

    return RaceSummarySchema(
        race_id=race.id,
        race_name=race.name,
        winner=winner,
        podium=podium,
        total_laps=race.total_laps or 0,
        total_drivers=len(results),
        finished_drivers=finished,
        dnf_count=dnf,
    )


@router.get("/{race_id}/results", response_model=list[ResultSchema])
async def get_race_results(
    race_id: int,
    db: Session = Depends(get_db_session),
) -> list[ResultSchema]:
    """
    Get race classification/results (per driver).
    """
    try:
        session = f1_queries.get_race_main_session(db, race_id)
    except Exception:
        raise race_not_found(race_id)

    results: list[DriverSessionResult] = f1_queries.get_race_results(db, session.id)

    return [
        ResultSchema(
            position=r.position,
            driver_code=r.driver.code,
            driver_name=r.driver.full_name,
            team=r.team.short_name,
            points=r.points,
            time_text=r.time_text,
            gap_to_winner_text=r.gap_to_winner_text,
            final_status=r.final_status,
            grid_position=r.grid_position,
        )
        for r in results
    ]


@router.get("/{race_id}/drivers", response_model=list[DriverWithTeamSchema])
async def get_race_drivers(
    race_id: int,
    db: Session = Depends(get_db_session),
) -> list[DriverWithTeamSchema]:
    """
    Get all drivers who participated in a race.
    """
    try:
        session = f1_queries.get_race_main_session(db, race_id)
    except Exception:
        raise race_not_found(race_id)

    results: list[DriverSessionResult] = f1_queries.get_race_results(db, session.id)

    return [
        DriverWithTeamSchema(
            id=r.driver.id,
            code=r.driver.code,
            full_name=r.driver.full_name,
            team=r.team.short_name,
        )
        for r in results
    ]
