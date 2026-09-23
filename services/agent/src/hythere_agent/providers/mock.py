from __future__ import annotations

import hashlib
import re

from .base import ProviderReply
from ..models import Turn

MOCK_REPLIES = [
    "Main Hythere AI companion hoon. Tum aaraam se bolo, main sun raha hoon.",
    "Samajh raha hoon. Aaj sabse heavy cheez kya lag rahi hai?",
    "Haan, ye kaafi tough lag raha hai. Thoda aur bataoge?",
    "Theek hai, ek ek step lete hain. Abhi dil mein sabse zyada kya chal raha hai?",
]


class MockLanguageModelProvider:
    async def generate_reply(self, *, turns: list[Turn], latest_user_text: str) -> ProviderReply:
        digest = hashlib.sha256(latest_user_text.encode("utf-8")).digest()[0]
        base = MOCK_REPLIES[digest % len(MOCK_REPLIES)]
        if len(turns) > 2:
            reply = f"{base} Tumne pehle jo bola tha, uske hisaab se lag raha hai ye cheez tum par build ho rahi hai."
        else:
            reply = base
        if latest_user_text.endswith("?"):
            reply += " Main short mein reply karunga, phir tum continue kar sakte ho."
        chunks = [chunk.strip() for chunk in re.split(r"(?<=[?.!।])\s+", reply) if chunk.strip()]
        return ProviderReply(text=reply, chunks=chunks or [reply], backend="mock")
