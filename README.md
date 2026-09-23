# Hythere

Hythere is a first MVP for a Hindi/Hinglish AI voice companion.

It is **an AI companion**, not a human, therapist, doctor, or emergency service.

## What is inside right now

This repository now has a small monorepo:

- `apps/web` - Next.js web app
- `services/api` - FastAPI session, config, health, and mock conversation API
- `services/agent` - reusable Python pipeline/session code and Sarvam/LiveKit-ready adapters
- `docs/deployment.md` - one concrete VPS + HTTPS + LiveKit Cloud deployment recipe

## What works today

### Works locally without API keys

A clearly labeled **mock demo mode** works with:

- microphone permission
- start / end / mute controls
- listening / thinking / speaking / error indicators
- optional ephemeral transcript on screen
- local-only opt-in auth guard for session creation
- in-memory session isolation
- short Hindi/Hinglish companion replies
- transcript clearing
- configurable distress-resource notice

### Prepared but not fully verified live path

The code also includes:

- LiveKit room token minting with short-lived scoped tokens
- verified package/model names from installable SDKs:
  - `livekit-client` `2.22.3`
  - `livekit-agents` `1.8.2`
  - `livekit-plugins-silero` `1.8.2`
  - `livekit-plugins-sarvam` `1.8.2`
  - `sarvamai` `0.1.34`
  - `livekit-api` `1.2.1`
- Sarvam model defaults wired as config, not hardcoded secrets:
  - chat LLM: `sarvam-105b`
  - streaming STT: `saaras:v4`
  - TTS: `bulbul:v3`
- Sarvam SDK adapters for Responses API, streaming STT websocket, and streaming TTS

## Important truth about the current MVP

The **fully server-hosted VAD -> STT -> Sarvam LLM -> TTS LiveKit worker is not fully verified in this sandbox**, because no real credentials were available here and the official docs domains were blocked from direct fetches during implementation.

What **was** verified from installable official SDK packages:

- LiveKit JS and Python package names and current versions
- LiveKit JWT token generation interface (`AccessToken`, `VideoGrants`)
- Official LiveKit Sarvam plugin module path (`livekit.plugins.sarvam`) with STT/TTS/LLM exports
- Sarvam Responses API model ids present in the SDK (`sarvam-105b`, `glm5.3`, `gemma4`, `deepseekv4-flash`)
- Sarvam streaming STT socket interface and supported default models in the SDK (`saaras:v3`, `saaras:v4`)
- Sarvam TTS streaming interface and current TTS models in the SDK (`bulbul:v2`, `bulbul:v3`)

So:

- the **mock path is working and testable now**
- the **live provider path is wired for the real SDKs**
- you should still run live smoke checks with your own credentials before calling it production-ready

## Easy local setup

### 1) Prerequisites

- Node.js **22+**
- Python **3.12+**

### 2) Install web dependencies

From the repository root:

```bash
npm install --prefix apps/web
```

### 3) Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements.txt -r services/agent/requirements.txt
```

### 4) Create env files

```bash
cp apps/web/.env.local.example apps/web/.env.local
cp services/api/.env.example services/api/.env
```

For the first local run, keep these values in `services/api/.env`:

```env
HYTHERE_ALLOW_LOCAL_DEV_AUTH=true
HYTHERE_MOCK_LLM_BACKEND=mock
```

Leave Sarvam and LiveKit credentials empty for the mock demo.

### 5) Start the API

```bash
source .venv/bin/activate
PYTHONPATH=services/api/src:services/agent/src uvicorn hythere_api.main:app --reload --app-dir services/api/src --host 127.0.0.1 --port 8000
```

### 6) Start the web app

In another terminal:

```bash
npm --prefix apps/web run dev
```

Open `http://127.0.0.1:3000`.

## How to test locally

### Mock demo path (no keys)

1. Open the web app.
2. Tick the consent checkbox.
3. Click **Start**.
4. Allow microphone permission.
5. Speak in Hindi or Hinglish.
6. If browser speech recognition is unavailable, use the **manual transcript fallback** box.
7. Click **End** when done.

### Optional live LLM only test with Sarvam

If you want real Sarvam text replies while still using browser speech helpers:

```env
HYTHERE_MOCK_LLM_BACKEND=sarvam
HYTHERE_SARVAM_API_SUBSCRIPTION_KEY=YOUR_KEY
HYTHERE_SARVAM_MODEL=sarvam-105b
```

Then restart the API.

This still does **not** prove live Sarvam STT/TTS quality or LiveKit room orchestration. It only proves the server-side Sarvam chat call.

### Optional LiveKit room token path

Add these to `services/api/.env`:

```env
HYTHERE_LIVEKIT_URL=wss://YOUR_PROJECT.livekit.cloud
HYTHERE_LIVEKIT_API_KEY=YOUR_KEY
HYTHERE_LIVEKIT_API_SECRET=YOUR_SECRET
```

Then restart the API. The web UI will enable **LiveKit room** mode.

## Exact test commands

### Web

```bash
npm run lint:web
npm run typecheck:web
npm run test:web
npm run build:web
```

### Python

```bash
source .venv/bin/activate
PYTHONPATH=services/api/src:services/agent/src pytest services/api/tests services/agent/tests
```

## What the tests cover

The deterministic tests cover:

- provider configuration guards
- normal mock pipeline replies
- distress notice insertion
- session isolation
- session caps
- local-only auth guard
- disabled live mode without credentials
- key frontend state transitions

The tests do **not** prove:

- live Hindi/Hinglish voice quality
- live Sarvam API compatibility on your account
- LiveKit worker barge-in behavior across real networked sessions

## Browser and device notes

- `localhost` on your laptop is only your laptop.
- Your phone cannot reach your laptop `localhost` unless you deploy the app somewhere reachable on your network and use proper HTTPS.
- Remote microphone use usually needs HTTPS.
- Browser autoplay rules may block audio until the user taps the page once.
- If you tunnel local dev to the public internet, **do not expose the local-only auth mode**.

## Privacy defaults

- no raw audio persistence by default
- no transcript persistence by default
- in-memory session state only
- transcript can be cleared from the UI
- provider keys stay server-side only

## Safety defaults

- the assistant clearly stays an AI companion
- it should not present itself as a person or therapist
- a distress notice can be configured with verified local support details
- no diagnostic or emotion-detection claims are made

## One-command container test

After creating `services/api/.env`:

```bash
docker compose up --build
```

Web: `http://127.0.0.1:3000`
API: `http://127.0.0.1:8000/healthz`

## Recommended next steps

1. Replace local-only auth with real user auth before public release.
2. Finish the long-running LiveKit worker that streams server-side STT -> Sarvam LLM -> TTS in-room.
3. Run live smoke tests with Hindi/Hinglish conversations, interruptions, two browser users, permission denial, disconnect/reconnect, and provider failures.
4. Measure end-of-turn to first-audio latency without storing private conversation content.
5. Only then move to mobile and optional consent-based memory.
