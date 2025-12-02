"""
Chat service for data-aware race Q&A using LLM.
"""
import json
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.services.llm_client import LLMClient
from app.services import f1_queries
from app.schemas.chat import ChatFocus, ChatResponse, UsedContext
from app.core.exceptions import DriverNotFoundException

logger = get_logger(__name__)


def build_system_prompt() -> str:
    """Build system prompt for the LLM."""
    return """You are an F1 race analysis assistant with deep knowledge of Formula 1 racing, strategy, and telemetry data.

Your role:
- Analyze F1 race data to provide insightful explanations about driver performance, race strategy, and race events
- Answer questions ONLY based on the structured race data provided in the context
- Focus on explaining pace differences, tyre strategy, pit stop timing, and relative performance using actual numbers
- Be concise but insightful - provide 1-3 short paragraphs

Important guidelines:
- If the provided data does not contain enough information to answer the question, explicitly say so
- NEVER invent facts or make assumptions beyond what the data shows
- Reference specific numbers from the data (lap times, stint averages, lap ranges) to support your analysis
- Explain WHY something happened based on the data patterns you observe
- Use F1 terminology appropriately (undercut, overcut, tyre degradation, delta, etc.)

When analyzing:
- Compare lap times and pace across stints
- Consider tyre compound effects on performance
- Look at consistency (standard deviation in lap times)
- Identify key moments (pit stops, pace changes)
- Consider track position and strategy implications"""


def build_context_dict(
    db: Session,
    race_id: int,
    session_id: int,
    driver_codes: list[str],
    lap_range: tuple[int, int] | None
) -> dict:
    """
    Build structured context dictionary with race data.
    
    Args:
        db: Database session
        race_id: Race ID
        session_id: Session ID
        driver_codes: List of driver codes to focus on
        lap_range: Optional lap range filter
        
    Returns:
        Dictionary with race context data
    """
    # Get race info
    race = f1_queries.get_race_by_id(db, race_id)
    
    # Get race results for context
    results = f1_queries.get_race_results(db, session_id)
    
    # Build podium
    podium = []
    for result in results[:3]:
        if result.position and result.position <= 3:
            podium.append({
                "position": result.position,
                "driver": result.driver.code,
                "team": result.team.short_name,
                "time": result.time_text
            })
    
    context = {
        "race": {
            "id": race_id,
            "name": race.name,
            "season": race.season.year,
            "round": race.round,
            "circuit": race.circuit_name,
            "country": race.country,
            "total_laps": race.total_laps,
            "date": race.date.isoformat()
        },
        "podium": podium,
        "lap_range": lap_range if lap_range else [1, race.total_laps or 0],
        "drivers": []
    }
    
    # If specific drivers requested, add detailed data for them
    if driver_codes:
        for code in driver_codes:
            try:
                driver = f1_queries.get_driver_by_code(db, code)
                
                # Get driver's result
                driver_result = next(
                    (r for r in results if r.driver_id == driver.id),
                    None
                )
                
                # Get stints
                stints = f1_queries.get_driver_stints(db, session_id, driver.id)
                stints_data = [
                    {
                        "stint": s.stint_number,
                        "compound": s.compound,
                        "laps": f"{s.start_lap}-{s.end_lap}",
                        "laps_count": s.laps_count,
                        "avg_lap_time_sec": round(s.avg_lap_time_sec, 3)
                    }
                    for s in stints
                ]
                
                # Get lap statistics
                lap_stats = f1_queries.get_lap_statistics(
                    db, session_id, driver.id, lap_range
                )
                
                # Get pit stop count
                pit_stops = f1_queries.count_pit_stops(db, session_id, driver.id)
                
                driver_data = {
                    "code": driver.code,
                    "name": driver.full_name,
                    "team": driver_result.team.short_name if driver_result else "Unknown",
                    "final_position": driver_result.position if driver_result else None,
                    "grid_position": driver_result.grid_position if driver_result else None,
                    "final_status": driver_result.final_status if driver_result else "Unknown",
                    "stints": stints_data,
                    "lap_statistics": lap_stats,
                    "pit_stops": pit_stops
                }
                
                context["drivers"].append(driver_data)
                
            except DriverNotFoundException:
                logger.warning(f"Driver {code} not found in race {race_id}")
                continue
    
    return context


async def answer_race_question(
    db: Session,
    race_id: int,
    question: str,
    driver_codes: list[str] | None,
    focus: ChatFocus,
    lap_range: tuple[int, int] | None,
    llm_client: LLMClient
) -> ChatResponse:
    """
    Answer a question about a race using LLM with race data context.
    
    Args:
        db: Database session
        race_id: Race ID
        question: User's question
        driver_codes: Optional list of driver codes to focus on (max 2)
        focus: Focus type (overall, driver, comparison)
        lap_range: Optional lap range to analyze
        llm_client: LLM client instance
        
    Returns:
        ChatResponse with answer and context used
        
    Raises:
        RaceNotFoundException: If race not found
        SessionNotFoundException: If race session not found
        LLMException: If LLM call fails
    """
    logger.info(f"Answering question for race {race_id}: {question[:100]}...")
    
    # Get race and session
    race = f1_queries.get_race_by_id(db, race_id)
    session = f1_queries.get_race_main_session(db, race_id)
    
    # Clean driver codes
    driver_codes = driver_codes or []
    driver_codes = [code.upper() for code in driver_codes[:2]]  # Max 2 drivers
    
    # Build context
    context = build_context_dict(
        db, 
        race_id, 
        session.id, 
        driver_codes, 
        lap_range
    )
    
    # Serialize context to JSON string
    context_json = json.dumps(context, indent=2)
    
    # Build user prompt
    user_prompt = f"""Question: {question}

Focus: {focus.value}

Race Data Context (JSON):
{context_json}

Based on the data above, please provide a concise analysis answering the question. Reference specific numbers from the data to support your explanation."""
    
    # Get system prompt
    system_prompt = build_system_prompt()
    
    # Call LLM
    logger.debug("Calling LLM...")
    answer = await llm_client.ask(system_prompt, user_prompt)
    logger.info(f"Received LLM response: {len(answer)} characters")
    
    # Build response
    short_stats = {}
    if context["drivers"]:
        for driver_data in context["drivers"]:
            short_stats[driver_data["code"]] = {
                "position": driver_data["final_position"],
                "stints": len(driver_data["stints"]),
                "pit_stops": driver_data["pit_stops"]
            }
    
    used_context = UsedContext(
        race_id=race_id,
        drivers=driver_codes,
        lap_range=lap_range,
        short_stats=short_stats
    )
    
    return ChatResponse(
        answer=answer,
        used_context=used_context
    )