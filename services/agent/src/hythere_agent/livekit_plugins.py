from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LiveKitPluginSummary:
    vad_module: str
    sarvam_module: str


def get_plugin_summary() -> LiveKitPluginSummary:
    from livekit.plugins import sarvam, silero

    return LiveKitPluginSummary(
        vad_module=silero.__name__,
        sarvam_module=sarvam.__name__,
    )
