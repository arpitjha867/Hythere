from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models import Turn


@dataclass(slots=True)
class ProviderReply:
    text: str
    chunks: list[str]
    backend: str


class LanguageModelProvider(Protocol):
    async def generate_reply(self, *, turns: list[Turn], latest_user_text: str) -> ProviderReply: ...
