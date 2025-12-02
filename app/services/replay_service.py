"""
Replay service for WebSocket telemetry streaming.
"""
import asyncio
from typing import AsyncGenerator
from sqlalchemy.orm import Session
from app.services import f1_queries
from app.models.telemetry import TelemetryFrame
from app.schemas.telemetry import ReplayFrameSchema, CarPositionSchema
from app.core.logging import get_logger

logger = get_logger(__name__)


def group_frames_by_driver(frames: list[TelemetryFrame]) -> dict[int, TelemetryFrame]:
    """
    Group telemetry frames by driver ID, keeping the latest frame for each driver.
    
    Args:
        frames: List of telemetry frames
        
    Returns:
        Dictionary mapping driver_id to latest TelemetryFrame
    """
    driver_frames: dict[int, TelemetryFrame] = {}
    for frame in frames:
        driver_frames[frame.driver_id] = frame
    return driver_frames


def build_replay_frame(current_time: float, frames: list[TelemetryFrame]) -> ReplayFrameSchema:
    """
    Build a replay frame from telemetry data.
    
    Args:
        current_time: Current replay time in seconds
        frames: Telemetry frames for this time window
        
    Returns:
        ReplayFrameSchema with car positions
    """
    # Group by driver to get latest position for each
    driver_frames = group_frames_by_driver(frames)
    
    # Build car positions
    cars = []
    for driver_id, frame in driver_frames.items():
        cars.append(
            CarPositionSchema(
                driver_code=frame.driver.code,
                x=frame.x_norm,
                y=frame.y_norm,
                speed_kph=frame.speed_kph,
                lap=frame.lap_number
            )
        )
    
    return ReplayFrameSchema(t=current_time, cars=cars)


async def generate_replay_frames(
    db: Session,
    session_id: int,
    fps: int = 10,
    driver_ids: list[int] | None = None
) -> AsyncGenerator[ReplayFrameSchema, None]:
    """
    Generate replay frames for a session as an async generator.
    
    Args:
        db: Database session
        session_id: Session ID to replay
        fps: Frames per second for replay
        driver_ids: Optional list of driver IDs to include (None = all drivers)
        
    Yields:
        ReplayFrameSchema objects at the specified FPS
    """
    logger.info(f"Starting replay for session {session_id} at {fps} FPS")
    
    # Load all telemetry frames
    telemetry_frames = f1_queries.get_telemetry_frames(db, session_id, driver_ids)
    
    if not telemetry_frames:
        logger.warning(f"No telemetry frames found for session {session_id}")
        return
    
    logger.info(f"Loaded {len(telemetry_frames)} telemetry frames")
    
    # Get time range
    min_time = min(frame.t_rel_sec for frame in telemetry_frames)
    max_time = max(frame.t_rel_sec for frame in telemetry_frames)
    
    logger.info(f"Time range: {min_time:.2f}s to {max_time:.2f}s")
    
    # Calculate time step
    time_step = 1.0 / fps
    current_time = min_time
    frame_index = 0
    
    # Pre-sort frames by time for efficient iteration
    telemetry_frames.sort(key=lambda f: f.t_rel_sec)
    
    while current_time <= max_time:
        # Collect frames within current time window
        window_frames = []
        window_end = current_time + time_step
        
        # Advance frame_index to current window
        while frame_index < len(telemetry_frames):
            frame = telemetry_frames[frame_index]
            if frame.t_rel_sec > window_end:
                break
            if frame.t_rel_sec >= current_time:
                window_frames.append(frame)
            frame_index += 1
        
        # Yield frame if we have data
        if window_frames:
            replay_frame = build_replay_frame(current_time, window_frames)
            yield replay_frame
        
        # Advance time and sleep
        current_time += time_step
        await asyncio.sleep(time_step)
        
        # Reset frame_index if needed (for overlapping windows)
        # In practice, we want to scan forward, so we keep advancing
        # But we might miss frames if they span multiple windows
        # For simplicity, we'll rely on grouping within each window
    
    logger.info(f"Replay completed for session {session_id}")


async def replay_session_websocket(
    db: Session,
    session_id: int,
    fps: int,
    send_callback: callable
) -> None:
    """
    Run replay and send frames via WebSocket callback.
    
    Args:
        db: Database session
        session_id: Session ID to replay
        fps: Frames per second
        send_callback: Async function to send data (e.g., websocket.send_json)
    """
    try:
        async for frame in generate_replay_frames(db, session_id, fps):
            await send_callback(frame.model_dump())
    except Exception as e:
        logger.error(f"Error during replay: {str(e)}")
        raise