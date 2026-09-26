# Deployment

This repository is designed for one simple deployment shape:

- **Web**: Next.js app on HTTPS
- **API**: FastAPI on HTTPS
- **Agent / pipeline worker**: long-running Python process on a VPS or VM, or the included Compose `agent` service
- **Media transport**: LiveKit Cloud for production WebRTC rooms

Do **not** run the long-running voice worker inside a short-lived serverless function.

## Recommended production recipe

1. Create one VPS or VM with Docker and Docker Compose.
2. Put Nginx or Caddy in front of the web and API containers.
3. Terminate TLS there so browsers use `https://` for the web app and `wss://` for LiveKit.
4. Keep `HYTHERE_LIVEKIT_API_SECRET`, `HYTHERE_SARVAM_API_SUBSCRIPTION_KEY`, and any future auth secrets in server-side environment files or a secret manager.
5. Set `HYTHERE_ALLOW_LOCAL_DEV_AUTH=false` in production.
6. Replace the local-only demo auth with real user auth before exposing the session endpoint publicly.
7. Restrict `HYTHERE_CORS_ORIGINS` to your real domain only.
8. Set a verified regional distress resource contact before any public launch.

## Container startup

```bash
cp services/api/.env.example services/api/.env
# edit services/api/.env with real values

docker compose up --build
```

To run the LiveKit voice worker, configure LiveKit and Sarvam credentials in `services/api/.env` and start the `livekit` profile:

```bash
docker compose --profile livekit up --build
```

## Health and smoke checks

After deploy, verify:

```bash
curl -f https://YOUR_DOMAIN/api/healthz
curl -f https://YOUR_DOMAIN/api/v1/config
```

Then run a browser smoke test:

1. Open the site over HTTPS.
2. Confirm microphone permission works.
3. Confirm the mock mode starts and ends cleanly.
4. Confirm the LiveKit agent worker is running before testing live voice mode.
5. If LiveKit and provider credentials are configured, test two separate browser sessions.
6. Interrupt the assistant mid-playback and confirm old playback stops.
7. Test permission denial, provider failure, and disconnect/reconnect.

## Reverse proxy notes

- Proxy `/` to the web app.
- Proxy `/api/` to the FastAPI service.
- Keep websocket upgrades enabled for LiveKit and any future streaming API routes.
- If you self-host LiveKit later, you must also handle TURN/media ports separately. That is different from this managed LiveKit Cloud recipe.

## Resource limits and cost control

- Keep a low `HYTHERE_MAX_CONCURRENT_SESSIONS` first.
- Watch LiveKit room counts, provider quotas, and API timeouts.
- The current in-memory session registry is single-instance only. If you scale the API horizontally, shared coordination storage will be required before claiming distributed safety.

## Rollback

- Keep the last working image tag.
- If a deploy fails smoke checks, roll back the web and API containers together.
- Because no raw audio or transcript persistence is enabled by default, rollback is operationally simpler.
