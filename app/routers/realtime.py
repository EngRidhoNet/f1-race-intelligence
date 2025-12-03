# app/routers/realtime.py
"""
Realtime race replay / live position endpoints (WebSocket).
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logging import get_logger

router = APIRouter(prefix="/realtime", tags=["Realtime"])

logger = get_logger(__name__)


@router.websocket("/echo")
async def echo_endpoint(websocket: WebSocket):
    """
    Simple echo WebSocket for testing.

    Gunakan dulu ini untuk cek bahwa frontend bisa connect ke WS:
    - connect ke ws://.../realtime/echo
    - kirim text, server akan balas text yang sama
    """
    await websocket.accept()
    logger.info("Echo client connected")

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(data)
    except WebSocketDisconnect:
        logger.info("Echo client disconnected")


@router.websocket("/race/{race_id}/session/{session_type}")
async def realtime_race_session(
    websocket: WebSocket,
    race_id: int,
    session_type: str,
):
    """
    Placeholder endpoint untuk real-time race replay per race + session type.

    Nanti bisa kamu sambung ke replay_service:
    - Ambil session_id dari race_id + session_type (via f1_queries)
    - Stream posisi mobil lap-by-lap atau frame-by-frame dari DB ke client

    Untuk sekarang, endpoint ini hanya mengirim pesan 'not implemented' lalu tutup.
    """
    await websocket.accept()
    await websocket.send_json(
        {
            "status": "not_implemented",
            "message": "Realtime replay belum diimplementasikan. Sambungkan ke replay_service di sini.",
            "race_id": race_id,
            "session_type": session_type,
        }
    )
    await websocket.close()
