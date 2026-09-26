from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, JobContext
from livekit.plugins import sarvam, silero

from . import LIVEKIT_AGENT_NAME
from .config import get_agent_settings
from .prompts import COMPANION_SYSTEM_PROMPT

load_dotenv(Path(__file__).resolve().parents[3] / "api" / ".env")

settings = get_agent_settings()
server = AgentServer(
    ws_url=settings.livekit_url,
    api_key=settings.livekit_api_key,
    api_secret=settings.livekit_api_secret,
)


@server.rtc_session(agent_name=LIVEKIT_AGENT_NAME)
async def run_voice_session(ctx: JobContext) -> None:
    if not settings.sarvam_api_subscription_key:
        raise RuntimeError("HYTHERE_SARVAM_API_SUBSCRIPTION_KEY is required for LiveKit voice sessions.")

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=sarvam.STT(
            language=settings.sarvam_stt_language,
            model=settings.sarvam_stt_model,
            mode=settings.sarvam_stt_mode,
            api_key=settings.sarvam_api_subscription_key,
        ),
        llm=sarvam.LLM(
            model=settings.sarvam_model,
            api_key=settings.sarvam_api_subscription_key,
        ),
        tts=sarvam.TTS(
            target_language_code=settings.sarvam_tts_language,
            model=settings.sarvam_tts_model,
            speaker=settings.sarvam_tts_speaker,
            api_key=settings.sarvam_api_subscription_key,
        ),
    )
    await session.start(room=ctx.room, agent=Agent(instructions=COMPANION_SYSTEM_PROMPT))


if __name__ == "__main__":
    agents.cli.run_app(server)