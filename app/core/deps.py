# app/core/deps.py
"""FastAPI dependencies."""
from typing import Generator
from sqlalchemy.orm import Session
from fastapi import Depends

from app.db import get_db
from app.config import Settings, get_settings
from app.services.llm_client import LLMClient, get_llm_client


def get_db_session() -> Generator[Session, None, None]:
    """Get database session dependency."""
    yield from get_db()


def get_app_settings() -> Settings:
    """Get application settings dependency."""
    return get_settings()


def get_llm() -> LLMClient:
    """Get LLM client dependency."""
    return get_llm_client(get_settings())