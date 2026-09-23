# Hythere

A Hindi/Hinglish voice-to-voice AI companion for web and, eventually, mobile clients.

## Implementation status

Repository initialized. The application is not implemented yet; executable setup and testing instructions will be added with the implementation.

## Planned first version

- Web voice interface with microphone controls and conversation status.
- Server-side voice pipeline: voice activity detection, speech recognition, Sarvam chat LLM, and speech synthesis.
- Isolated user sessions, interruption handling, and server-side provider credentials.
- Local mock tests, optional live provider tests, and step-by-step deployment documentation.

## Privacy and safety

Hythere is intended to be an AI companion, not a human, therapist, or emergency service. Cloud voice features send audio/text to configured providers. Raw audio and conversation history should not be retained by default.

Do not commit API keys, credentials, recordings, or personal conversation transcripts to this public repository.
