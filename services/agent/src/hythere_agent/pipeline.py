from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .config import AgentSettings
from .errors import ProviderError
from .providers.base import ProviderReply
from .providers.mock import MockLanguageModelProvider
from .providers.sarvam import SarvamLanguageModelProvider
from .registry import SessionRegistry
from .safety import DistressAssessment, DistressResource, assess_distress


@dataclass(slots=True)
class PipelineReply:
    reply_text: str
    chunks: list[str]
    backend: str
    distress_notice: str | None


class CompanionPipeline:
    def __init__(self, settings: AgentSettings, registry: SessionRegistry) -> None:
        self._settings = settings
        self._registry = registry
        self._provider = self._build_provider()

    def _build_provider(self):
        if self._settings.mock_llm_backend == "sarvam":
            if not self._settings.sarvam_api_subscription_key:
                raise ProviderError("Sarvam backend selected but HYTHERE_SARVAM_API_SUBSCRIPTION_KEY is missing.")
            return SarvamLanguageModelProvider(
                api_key=self._settings.sarvam_api_subscription_key,
                model=self._settings.sarvam_model,
            )
        return MockLanguageModelProvider()

    async def respond(self, *, session_id: str, transcript: str) -> PipelineReply:
        session, generation = self._registry.begin_turn(session_id, transcript)
        assessment = assess_distress(
            transcript,
            DistressResource(
                name=self._settings.distress_resource_name,
                contact=self._settings.distress_resource_contact,
                region=self._settings.distress_resource_region,
            ),
        )

        reply = await asyncio.wait_for(
            self._provider.generate_reply(turns=session.turns[:-1], latest_user_text=transcript),
            timeout=self._settings.response_timeout_seconds,
        )

        if not self._registry.is_current_generation(session_id, generation):
            return PipelineReply(reply_text="", chunks=[], backend=reply.backend, distress_notice=assessment.notice)

        merged = self._merge_safety_notice(reply, assessment)
        self._registry.complete_turn(session_id, generation, merged.text)
        return PipelineReply(
            reply_text=merged.text,
            chunks=merged.chunks,
            backend=merged.backend,
            distress_notice=assessment.notice,
        )

    @staticmethod
    def _merge_safety_notice(reply: ProviderReply, assessment: DistressAssessment) -> ProviderReply:
        if not assessment.notice:
            return reply
        combined_text = f"{assessment.notice} {reply.text}".strip()
        combined_chunks = [assessment.notice, *reply.chunks]
        return ProviderReply(text=combined_text, chunks=combined_chunks, backend=reply.backend)
