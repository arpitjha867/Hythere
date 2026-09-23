from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Turn:
    role: Literal["user", "assistant"]
    text: str


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    mode: Literal["mock", "livekit"]
    created_at: datetime
    expires_at: datetime
    room_name: str | None = None
    identity: str | None = None
    generation: int = 0
    closed: bool = False
    turns: list[Turn] = field(default_factory=list)

    def touch_generation(self) -> int:
        self.generation += 1
        return self.generation

    def trim_history(self, max_turns: int) -> None:
        if len(self.turns) > max_turns:
            self.turns = self.turns[-max_turns:]

    @classmethod
    def build(cls, *, session_id: str, mode: Literal["mock", "livekit"], ttl_minutes: int, room_name: str | None = None, identity: str | None = None) -> "SessionRecord":
        now = utc_now()
        return cls(
            session_id=session_id,
            mode=mode,
            created_at=now,
            expires_at=now + timedelta(minutes=ttl_minutes),
            room_name=room_name,
            identity=identity,
        )
