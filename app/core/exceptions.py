# app/core/exceptions.py
"""Custom exceptions."""
from fastapi import HTTPException, status


class F1IntelligenceException(Exception):
    """Base exception for F1 Intelligence application."""
    pass


class RaceNotFoundException(F1IntelligenceException):
    """Raised when a race is not found."""
    pass


class SessionNotFoundException(F1IntelligenceException):
    """Raised when a session is not found."""
    pass


class DriverNotFoundException(F1IntelligenceException):
    """Raised when a driver is not found."""
    pass


class LLMException(F1IntelligenceException):
    """Raised when LLM call fails."""
    pass


def race_not_found(race_id: int) -> HTTPException:
    """Create HTTPException for race not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Race with ID {race_id} not found"
    )


def session_not_found(session_id: int) -> HTTPException:
    """Create HTTPException for session not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Session with ID {session_id} not found"
    )


def driver_not_found(driver_code: str) -> HTTPException:
    """Create HTTPException for driver not found."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Driver with code {driver_code} not found"
    )


def llm_error(message: str) -> HTTPException:
    """Create HTTPException for LLM errors."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"LLM error: {message}"
    )