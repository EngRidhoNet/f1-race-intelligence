# app/routers/chat.py
"""Chatbot endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db_session, get_llm
from app.core.exceptions import race_not_found, llm_error
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_client import LLMClient
from app.services.chat_service import answer_race_question
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/races", tags=["Chat"])


@router.post("/{race_id}/chat", response_model=ChatResponse)
async def chat_about_race(
    race_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db_session),
    llm_client: LLMClient = Depends(get_llm)
) -> ChatResponse:
    """
    Ask a question about a race and get an AI-powered answer based on race data.
    
    The chatbot analyzes actual race data (laps, stints, telemetry) and uses an LLM
    to provide natural language explanations.
    
    Example questions:
    - "Why was Leclerc slower in the second stint?"
    - "How did Verstappen's strategy differ from Hamilton's?"
    - "What caused the gap between P1 and P2?"
    """
    try:
        logger.info(f"Chat request for race {race_id}: {request.question[:100]}")
        
        response = await answer_race_question(
            db=db,
            race_id=race_id,
            question=request.question,
            driver_codes=request.driver_codes,
            focus=request.focus,
            lap_range=request.lap_range,
            llm_client=llm_client
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise llm_error(str(e))


# app/routers/realtime.py
"""WebSocket realtime replay endpoint."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db_session, get_app_settings
from app.core.logging import get_logger
from app.config import Settings
from app.services import replay_service

logger = get_logger(__name__)
router = APIRouter(tags=["Realtime"])


@router.websocket("/ws/races/{race_id}/replay")
async def replay_race(
    websocket: WebSocket,
    race_id: int,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings)
):
    """
    WebSocket endpoint for replaying race telemetry.
    
    Streams car positions frame-by-frame for visualization on a track map.
    
    Usage:
        ws = new WebSocket("ws://localhost:8000/ws/races/123/replay")
        ws.onmessage = (event) => {
            const frame = JSON.parse(event.data)
            // frame.t: current time in seconds
            // frame.cars: array of {driver_code, x, y, speed_kph, lap}
        }
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for race {race_id} replay")
    
    try:
        # Get session
        from app.services import f1_queries
        session = f1_queries.get_race_main_session(db, race_id)
        
        # Start replay
        await replay_service.replay_session_websocket(
            db=db,
            session_id=session.id,
            fps=settings.replay_fps,
            send_callback=websocket.send_json
        )
        
        # Send completion message
        await websocket.send_json({"status": "complete"})
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for race {race_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass