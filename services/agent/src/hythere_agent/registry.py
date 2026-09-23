from __future__ import annotations

import secrets
from typing import Literal

from .errors import SessionLimitError, SessionNotFoundError
from .models import SessionRecord, Turn, utc_now


class SessionRegistry:
    def __init__(self, *, max_sessions: int, ttl_minutes: int, history_turn_limit: int) -> None:
        self._sessions: dict[str, SessionRecord] = {}
        self._max_sessions = max_sessions
        self._ttl_minutes = ttl_minutes
        self._history_turn_limit = history_turn_limit

    def create(self, *, mode: Literal["mock", "livekit"], room_name: str | None = None, identity: str | None = None) -> SessionRecord:
        self.cleanup_expired()
        if len(self._sessions) >= self._max_sessions:
            raise SessionLimitError("The server is busy right now. Please try again shortly.")
        session = SessionRecord.build(
            session_id=f"session_{secrets.token_hex(6)}",
            mode=mode,
            ttl_minutes=self._ttl_minutes,
            room_name=room_name,
            identity=identity,
        )
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> SessionRecord:
        self.cleanup_expired()
        session = self._sessions.get(session_id)
        if session is None or session.closed:
            raise SessionNotFoundError("That session is no longer active.")
        return session

    def close(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is not None:
            session.closed = True
            self._sessions.pop(session_id, None)

    def begin_turn(self, session_id: str, transcript: str) -> tuple[SessionRecord, int]:
        session = self.get(session_id)
        generation = session.touch_generation()
        session.turns.append(Turn(role="user", text=transcript))
        session.trim_history(self._history_turn_limit)
        return session, generation

    def complete_turn(self, session_id: str, generation: int, reply_text: str) -> None:
        session = self.get(session_id)
        if session.generation != generation:
            return
        session.turns.append(Turn(role="assistant", text=reply_text))
        session.trim_history(self._history_turn_limit)

    def is_current_generation(self, session_id: str, generation: int) -> bool:
        session = self.get(session_id)
        return session.generation == generation

    def cleanup_expired(self) -> None:
        now = utc_now()
        expired = [session_id for session_id, session in self._sessions.items() if session.expires_at <= now or session.closed]
        for session_id in expired:
            self._sessions.pop(session_id, None)
