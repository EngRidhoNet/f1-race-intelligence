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

"""
F1 data ingestion service - Part 2: Laps, Stints, Telemetry, Track Shape
"""

def ingest_laps(
    db: Session,
    session: SessionModel,
    ff1_session: fastf1.core.Session
) -> None:
    """
    Ingest lap data.
    
    Args:
        db: Database session
        session: Session model
        ff1_session: FastF1 session object
    """
    laps_df = ff1_session.laps
    
    if laps_df is None or laps_df.empty:
        logger.warning("No laps data available")
        return
    
    logger.info(f"Ingesting {len(laps_df)} laps...")
    
    # Delete existing laps for this session
    db.query(Lap).filter(Lap.session_id == session.id).delete()
    
    for idx, lap_row in laps_df.iterrows():
        # Get driver
        driver_code = str(lap_row.get('Driver', 'UNK'))
        stmt = select(Driver).where(Driver.code == driver_code)
        driver = db.execute(stmt).scalar_one_or_none()
        
        if not driver:
            logger.warning(f"Driver {driver_code} not found for lap, skipping")
            continue
        
        # Parse lap number
        lap_number = int(lap_row.get('LapNumber', 0))
        
        # Parse lap time
        lap_time_sec = None
        if pd.notna(lap_row.get('LapTime')):
            try:
                lap_time_sec = lap_row['LapTime'].total_seconds()
            except:
                pass
        
        # Parse sector times
        sector1 = None
        sector2 = None
        sector3 = None
        
        if pd.notna(lap_row.get('Sector1Time')):
            try:
                sector1 = lap_row['Sector1Time'].total_seconds()
            except:
                pass
        
        if pd.notna(lap_row.get('Sector2Time')):
            try:
                sector2 = lap_row['Sector2Time'].total_seconds()
            except:
                pass
        
        if pd.notna(lap_row.get('Sector3Time')):
            try:
                sector3 = lap_row['Sector3Time'].total_seconds()
            except:
                pass
        
        # Parse pit lap
        is_pit = bool(lap_row.get('PitInTime') is not pd.NaT or lap_row.get('PitOutTime') is not pd.NaT)
        
        # Tyre info
        compound = str(lap_row.get('Compound', '')) if pd.notna(lap_row.get('Compound')) else None
        tyre_life = int(lap_row.get('TyreLife', 0)) if pd.notna(lap_row.get('TyreLife')) else None
        
        # Track status
        track_status = str(lap_row.get('TrackStatus', '')) if pd.notna(lap_row.get('TrackStatus')) else None
        
        lap = Lap(
            session_id=session.id,
            driver_id=driver.id,
            lap_number=lap_number,
            lap_time_sec=lap_time_sec,
            sector1_time_sec=sector1,
            sector2_time_sec=sector2,
            sector3_time_sec=sector3,
            is_pit_lap=is_pit,
            tyre_compound=compound,
            tyre_life_laps=tyre_life,
            track_status=track_status
        )
        db.add(lap)
    
    db.flush()
    logger.info("Laps ingestion complete")


def derive_stints(
    db: Session,
    session: SessionModel,
    ff1_session: fastf1.core.Session
) -> None:
    """
    Derive and ingest stint data from laps.
    
    Args:
        db: Database session
        session: Session model
        ff1_session: FastF1 session object
    """
    logger.info("Deriving stints from laps...")
    
    # Delete existing stints
    db.query(Stint).filter(Stint.session_id == session.id).delete()
    
    laps_df = ff1_session.laps
    if laps_df is None or laps_df.empty:
        return
    
    # Group by driver
    for driver_code in laps_df['Driver'].unique():
        driver_laps = laps_df[laps_df['Driver'] == driver_code].copy()
        driver_laps = driver_laps.sort_values('LapNumber')
        
        # Get driver
        stmt = select(Driver).where(Driver.code == driver_code)
        driver = db.execute(stmt).scalar_one_or_none()
        if not driver:
            continue
        
        # Identify stint changes (compound changes)
        current_compound = None
        stint_number = 0
        stint_laps = []
        
        for idx, lap_row in driver_laps.iterrows():
            compound = str(lap_row.get('Compound', ''))
            lap_num = int(lap_row.get('LapNumber', 0))
            lap_time = lap_row.get('LapTime')
            
            # Skip if no compound or pit lap
            if pd.isna(compound) or compound == '' or compound == 'nan':
                continue
            
            # New stint detected
            if compound != current_compound:
                # Save previous stint
                if stint_laps:
                    valid_times = [t for t in stint_laps if pd.notna(t)]
                    if valid_times:
                        avg_time = sum(t.total_seconds() for t in valid_times) / len(valid_times)
                        stint = Stint(
                            session_id=session.id,
                            driver_id=driver.id,
                            stint_number=stint_number,
                            start_lap=stint_laps[0][0],
                            end_lap=stint_laps[-1][0],
                            compound=current_compound,
                            avg_lap_time_sec=avg_time,
                            laps_count=len(stint_laps)
                        )
                        db.add(stint)
                
                # Start new stint
                stint_number += 1
                current_compound = compound
                stint_laps = []
            
            stint_laps.append((lap_num, lap_time))
        
        # Save last stint
        if stint_laps and current_compound:
            valid_times = [t for t in [lt[1] for lt in stint_laps] if pd.notna(t)]
            if valid_times:
                avg_time = sum(t.total_seconds() for t in valid_times) / len(valid_times)
                stint = Stint(
                    session_id=session.id,
                    driver_id=driver.id,
                    stint_number=stint_number,
                    start_lap=stint_laps[0][0],
                    end_lap=stint_laps[-1][0],
                    compound=current_compound,
                    avg_lap_time_sec=avg_time,
                    laps_count=len(stint_laps)
                )
                db.add(stint)
    
    db.flush()
    logger.info("Stints derivation complete")


def ingest_telemetry(
    db: Session,
    session: SessionModel,
    race: Race,
    ff1_session: fastf1.core.Session,
    sample_rate: int = 10
) -> None:
    """
    Ingest telemetry data (positions, speed, etc.).
    Samples data to reduce volume.
    
    Args:
        db: Database session
        session: Session model
        race: Race model
        ff1_session: FastF1 session object
        sample_rate: Keep every Nth telemetry point
    """
    logger.info(f"Ingesting telemetry (sample rate: 1/{sample_rate})...")
    
    # Delete existing telemetry for this session
    db.query(TelemetryFrame).filter(TelemetryFrame.session_id == session.id).delete()
    
    # Collect all telemetry data
    all_x = []
    all_y = []
    
    laps_df = ff1_session.laps
    if laps_df is None or laps_df.empty:
        logger.warning("No laps for telemetry")
        return
    
    # First pass: collect all coordinates for normalization
    for driver_code in laps_df['Driver'].unique():
        driver_laps = laps_df[laps_df['Driver'] == driver_code]
        for idx, lap in driver_laps.iterrows():
            try:
                telemetry = lap.get_telemetry()
                if telemetry is not None and not telemetry.empty:
                    all_x.extend(telemetry['X'].values)
                    all_y.extend(telemetry['Y'].values)
            except:
                continue
    
    if not all_x or not all_y:
        logger.warning("No telemetry data available")
        return
    
    # Normalize coordinates
    all_x = np.array(all_x)
    all_y = np.array(all_y)
    x_min, x_max = all_x.min(), all_x.max()
    y_min, y_max = all_y.min(), all_y.max()
    
    logger.info(f"Coordinate ranges: X[{x_min:.2f}, {x_max:.2f}], Y[{y_min:.2f}, {y_max:.2f}]")
    
    # Second pass: ingest sampled telemetry
    for driver_code in laps_df['Driver'].unique():
        # Get driver
        stmt = select(Driver).where(Driver.code == driver_code)
        driver = db.execute(stmt).scalar_one_or_none()
        if not driver:
            continue
        
        driver_laps = laps_df[laps_df['Driver'] == driver_code]
        
        for idx, lap in driver_laps.iterrows():
            lap_number = int(lap.get('LapNumber', 0))
            
            try:
                telemetry = lap.get_telemetry()
                if telemetry is None or telemetry.empty:
                    continue
                
                # Sample telemetry
                telemetry = telemetry.iloc[::sample_rate]
                
                for t_idx, t_row in telemetry.iterrows():
                    # Normalize coordinates
                    x = float(t_row.get('X', 0))
                    y = float(t_row.get('Y', 0))
                    x_norm = (x - x_min) / (x_max - x_min) if x_max > x_min else 0.5
                    y_norm = (y - y_min) / (y_max - y_min) if y_max > y_min else 0.5
                    
                    # Time relative to session start
                    t_rel = float(t_row.get('Time', 0).total_seconds()) if pd.notna(t_row.get('Time')) else 0.0
                    
                    # Other channels
                    speed = float(t_row.get('Speed', 0)) if pd.notna(t_row.get('Speed')) else None
                    throttle = float(t_row.get('Throttle', 0)) / 100.0 if pd.notna(t_row.get('Throttle')) else None
                    brake = 1.0 if t_row.get('Brake', False) else 0.0
                    gear = int(t_row.get('nGear', 0)) if pd.notna(t_row.get('nGear')) else None
                    
                    frame = TelemetryFrame(
                        session_id=session.id,
                        driver_id=driver.id,
                        t_rel_sec=t_rel,
                        lap_number=lap_number,
                        x_norm=x_norm,
                        y_norm=y_norm,
                        speed_kph=speed,
                        throttle=throttle,
                        brake=brake,
                        gear=gear
                    )
                    db.add(frame)
                
            except Exception as e:
                logger.warning(f"Error processing telemetry for {driver_code} lap {lap_number}: {e}")
                continue
    
    db.flush()
    logger.info("Telemetry ingestion complete")


# Continue in Part 3 for track shape and main function...

"""
F1 data ingestion service - Part 3: Track Shape and Main Function
"""

def ingest_track_shape(
    db: Session,
    race: Race,
    ff1_session: fastf1.core.Session,
    decimate_factor: int = 20
) -> None:
    """
    Derive and ingest track shape polyline from a reference lap.
    
    Args:
        db: Database session
        race: Race model
        ff1_session: FastF1 session object
        decimate_factor: Keep every Nth point for track shape
    """
    logger.info("Deriving track shape...")
    
    # Delete existing track shape
    db.query(TrackShapePoint).filter(TrackShapePoint.race_id == race.id).delete()
    
    laps_df = ff1_session.laps
    if laps_df is None or laps_df.empty:
        logger.warning("No laps available for track shape")
        return
    
    # Find a good reference lap (fastest lap from the winner or first driver)
    try:
        fastest_lap = laps_df.pick_fastest()
        if fastest_lap is None:
            logger.warning("No fastest lap found")
            return
        
        telemetry = fastest_lap.get_telemetry()
        if telemetry is None or telemetry.empty:
            logger.warning("No telemetry for fastest lap")
            return
        
        # Get X, Y coordinates
        x_values = telemetry['X'].values
        y_values = telemetry['Y'].values
        
        # Normalize
        x_norm, y_norm = normalize_coordinates(x_values, y_values)
        
        # Decimate (sample every Nth point)
        x_norm = x_norm[::decimate_factor]
        y_norm = y_norm[::decimate_factor]
        
        # Create track shape points
        for order_idx, (x, y) in enumerate(zip(x_norm, y_norm)):
            point = TrackShapePoint(
                race_id=race.id,
                order_index=order_idx,
                x_norm=float(x),
                y_norm=float(y)
            )
            db.add(point)
        
        db.flush()
        logger.info(f"Created track shape with {len(x_norm)} points")
        
    except Exception as e:
        logger.error(f"Error creating track shape: {e}")


def ingest_race_data(year: int, round_num: int) -> None:
    """
    Main ingestion function for a specific race.
    
    Args:
        year: Season year
        round_num: Race round number
    """
    settings = get_settings()
    
    # Enable FastF1 cache
    fastf1.Cache.enable_cache(settings.fastf1_cache_dir)
    logger.info(f"FastF1 cache enabled at: {settings.fastf1_cache_dir}")
    
    # Load FastF1 session
    logger.info(f"Loading F1 session: {year} Round {round_num}")
    try:
        ff1_session = fastf1.get_session(year, round_num, 'R')  # 'R' for Race
        ff1_session.load()
        logger.info(f"Loaded session: {ff1_session.event['EventName']}")
    except Exception as e:
        logger.error(f"Failed to load FastF1 session: {e}")
        return
    
    # Create database session
    db = SessionLocal()
    
    try:
        logger.info("Starting database ingestion...")
        
        # Step 1: Ingest race metadata
        season, race, session = ingest_race_metadata(db, ff1_session)
        db.commit()
        logger.info(f"✓ Metadata ingested: {race.name}")
        
        # Step 2: Ingest results
        ingest_results(db, session, ff1_session)
        db.commit()
        logger.info("✓ Results ingested")
        
        # Step 3: Ingest laps
        ingest_laps(db, session, ff1_session)
        db.commit()
        logger.info("✓ Laps ingested")
        
        # Step 4: Derive stints
        derive_stints(db, session, ff1_session)
        db.commit()
        logger.info("✓ Stints derived")
        
        # Step 5: Ingest telemetry (sampled)
        ingest_telemetry(db, session, race, ff1_session, sample_rate=10)
        db.commit()
        logger.info("✓ Telemetry ingested")
        
        # Step 6: Create track shape
        ingest_track_shape(db, race, ff1_session, decimate_factor=20)
        db.commit()
        logger.info("✓ Track shape created")
        
        logger.info(f"✅ Successfully ingested {year} Round {round_num}: {race.name}")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """CLI entrypoint for ingestion script."""
    parser = argparse.ArgumentParser(
        description="Ingest F1 race data from FastF1 into PostgreSQL"
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Season year (e.g., 2024)"
    )
    parser.add_argument(
        "--round",
        type=int,
        required=True,
        help="Race round number (e.g., 1 for first race)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Run ingestion
    logger.info("=" * 60)
    logger.info(f"F1 Data Ingestion: {args.year} Round {args.round}")
    logger.info("=" * 60)
    
    ingest_race_data(args.year, args.round)
    
    logger.info("=" * 60)
    logger.info("Ingestion complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()