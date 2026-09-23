from __future__ import annotations

import re

from sarvamai import AsyncSarvamAI
from sarvamai.types.response_output_message import ResponseOutputMessage

from ..errors import ProviderError
from ..models import Turn
from ..prompts import COMPANION_SYSTEM_PROMPT
from .base import ProviderReply


class SarvamLanguageModelProvider:
    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = AsyncSarvamAI(api_subscription_key=api_key)
        self._model = model

    async def generate_reply(self, *, turns: list[Turn], latest_user_text: str) -> ProviderReply:
        messages = [{"role": "system", "content": COMPANION_SYSTEM_PROMPT}]
        for turn in turns:
            messages.append({"role": turn.role, "content": turn.text})
        messages.append({"role": "user", "content": latest_user_text})
        try:
            response = await self._client.responses.create(
                model=self._model,
                input=messages,
                store=False,
                max_output_tokens=220,
                temperature=0.6,
            )
        except Exception as exc:  # pragma: no cover - upstream specifics vary
            raise ProviderError("Sarvam LLM request failed.") from exc

        text_parts: list[str] = []
        for item in response.output:
            if isinstance(item, ResponseOutputMessage) and item.role == "assistant" and item.content:
                text_parts.extend(part.text for part in item.content if getattr(part, "text", None))
        reply_text = " ".join(part.strip() for part in text_parts if part.strip()).strip()
        if not reply_text:
            raise ProviderError("Sarvam LLM returned an empty reply.")
        chunks = [chunk.strip() for chunk in re.split(r"(?<=[?.!।])\s+", reply_text) if chunk.strip()]
        return ProviderReply(text=reply_text, chunks=chunks or [reply_text], backend=f"sarvam:{self._model}")
