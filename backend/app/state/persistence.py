"""
State persistence layer — SQLite via SQLAlchemy async.
Stores session state snapshots and event logs.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import Column, String, Text, DateTime, Integer, select
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import settings
from app.state.models import RAAHATState

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True)
    state_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    plan_version = Column(Integer, default=1)
    is_complete = Column(Integer, default=0)  # SQLite bool


class EventRecord(Base):
    __tablename__ = "events"

    event_id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    agent = Column(String)
    message = Column(Text)
    data_json = Column(Text, default="{}")
    timestamp = Column(String)
    status = Column(String, default="info")


# Global engine / session factory (initialized once on startup)
_engine = None
_session_factory = None


async def init_db() -> None:
    """Initialize the database and create tables."""
    global _engine, _session_factory
    _engine = create_async_engine(settings.database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized at %s", settings.database_url)


def _get_session_factory():
    return _session_factory


# In-memory fast cache of active states so live updates are instantaneous
_live_states: Dict[str, RAAHATState] = {}


async def save_state(state: RAAHATState) -> None:
    """Persist the full state snapshot to in-memory cache and SQLite."""
    _live_states[state.session_id] = state
    if _session_factory is None:
        return
    try:
        async with _session_factory() as session:
            async with session.begin():
                existing = await session.get(SessionRecord, state.session_id)
                state_json = state.model_dump_json()
                if existing:
                    existing.state_json = state_json
                    existing.updated_at = datetime.utcnow()
                    existing.plan_version = state.plan_version
                    existing.is_complete = int(state.is_complete)
                else:
                    session.add(
                        SessionRecord(
                            session_id=state.session_id,
                            state_json=state_json,
                            plan_version=state.plan_version,
                            is_complete=int(state.is_complete),
                        )
                    )
    except Exception as e:
        logger.warning("Error saving state to SQLite for session %s: %s", state.session_id, e)


async def load_state(session_id: str) -> Optional[RAAHATState]:
    """Load a state snapshot from memory cache, falling back to SQLite."""
    if session_id in _live_states:
        return _live_states[session_id]
    if _session_factory is None:
        return None
    try:
        async with _session_factory() as session:
            record = await session.get(SessionRecord, session_id)
            if record:
                st = RAAHATState.model_validate_json(record.state_json)
                _live_states[session_id] = st
                return st
    except Exception as e:
        logger.warning("Error loading state from SQLite for session %s: %s", session_id, e)
    return None


def get_live_state(session_id: str) -> Optional[RAAHATState]:
    """Synchronously get current in-memory state snapshot if available."""
    return _live_states.get(session_id)



async def save_event(session_id: str, event_dict: dict) -> None:
    """Persist an individual event to the events table."""
    if _session_factory is None:
        return
    async with _session_factory() as session:
        async with session.begin():
            session.add(
                EventRecord(
                    event_id=event_dict.get("event_id", ""),
                    session_id=session_id,
                    event_type=event_dict.get("event_type", ""),
                    agent=event_dict.get("agent"),
                    message=event_dict.get("message", ""),
                    data_json=json.dumps(event_dict.get("data", {})),
                    timestamp=event_dict.get("timestamp"),
                    status=event_dict.get("status", "info"),
                )
            )
