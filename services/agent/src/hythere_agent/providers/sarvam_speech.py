from __future__ import annotations

from typing import AsyncIterator

from sarvamai import AsyncSarvamAI


class SarvamSpeechClients:
    def __init__(self, *, api_key: str) -> None:
        self._client = AsyncSarvamAI(api_subscription_key=api_key)

    def streaming_stt_socket(self, *, language_code: str = "hi-IN", model: str = "saaras:v4", mode: str = "codemix"):
        return self._client.speech_to_text_streaming.connect(
            language_code=language_code,
            model=model,
            mode=mode,
            input_audio_codec="wav",
            sample_rate="16000",
        )

    async def tts_stream(
        self,
        *,
        text: str,
        speaker: str = "shubh",
        model: str = "bulbul:v3",
        language_code: str = "hi-IN",
    ) -> AsyncIterator[bytes]:
        async for chunk in self._client.text_to_speech.convert_stream(
            text=text,
            speaker=speaker,
            model=model,
            language_code=language_code,
            output_audio_codec="mp3",
        ):
            yield chunk
