# app/schemas/chat.py
"""Chat-related schemas."""
from enum import Enum
from pydantic import BaseModel, Field


class ChatFocus(str, Enum):
    """Chat focus type."""
    OVERALL = "overall"
    DRIVER = "driver"
    COMPARISON = "comparison"


class ChatRequest(BaseModel):
    """Chat request schema."""
    question: str = Field(..., min_length=1, max_length=1000)
    driver_codes: list[str] = Field(default_factory=list, max_length=2)
    focus: ChatFocus = ChatFocus.OVERALL
    lap_range: tuple[int, int] | None = None


class UsedContext(BaseModel):
    """Context used for chat response."""
    race_id: int
    drivers: list[str]
    lap_range: tuple[int, int] | None
    short_stats: dict


class ChatResponse(BaseModel):
    """Chat response schema."""
    answer: str
    used_context: UsedContext