from hythere_agent.livekit_plugins import get_plugin_summary


def test_livekit_plugin_modules_import() -> None:
    summary = get_plugin_summary()

    assert summary.vad_module == "livekit.plugins.silero"
    assert summary.sarvam_module == "livekit.plugins.sarvam"
