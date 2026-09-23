"use client";

import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import styles from "@/app/page.module.css";
import { initialVoiceState, statusLabel, voiceReducer } from "@/lib/voice-state";

interface PublicConfig {
  mock_enabled: boolean;
  livekit_enabled: boolean;
  local_dev_auth_enabled: boolean;
  max_session_minutes: number;
  max_concurrent_sessions: number;
  distress_resource_configured: boolean;
  mock_llm_backend: string;
  livekit_url?: string | null;
}

interface SessionResponse {
  session_id: string;
  mode: "mock" | "livekit";
  expires_in_seconds: number;
  livekit_url?: string | null;
  livekit_room?: string | null;
  livekit_identity?: string | null;
  livekit_token?: string | null;
}

interface MockReplyResponse {
  session_id: string;
  reply_text: string;
  chunks: string[];
  backend: string;
  distress_notice: string | null;
}

type RecognitionResult = {
  finalText: string;
  interimText?: string;
};

type BrowserRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

declare global {
  interface Window {
    SpeechRecognition?: new () => BrowserRecognition;
    webkitSpeechRecognition?: new () => BrowserRecognition;
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

export function VoiceConsole() {
  const [state, dispatch] = useReducer(voiceReducer, initialVoiceState);
  const [consent, setConsent] = useState(false);
  const [showTranscript, setShowTranscript] = useState(true);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [mode, setMode] = useState<"mock" | "livekit">("mock");
  const [micPermission, setMicPermission] = useState("unknown");
  const [manualTranscript, setManualTranscript] = useState("");
  const [liveKitSummary, setLiveKitSummary] = useState("Not connected");
  const [backendSummary, setBackendSummary] = useState("mock");
  const roomRef = useRef<unknown>(null);
  const stateRef = useRef(state);
  const speechAbortRef = useRef<AbortController | null>(null);
  const recognitionRef = useRef<BrowserRecognition | null>(null);
  const activeUtterances = useRef<SpeechSynthesisUtterance[]>([]);
  const turnCounterRef = useRef(0);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    void fetch(`${API_BASE}/v1/config`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(await response.text());
        }
        return response.json() as Promise<PublicConfig>;
      })
      .then((json) => {
        setConfig(json);
        setMode(json.livekit_enabled ? "livekit" : "mock");
        setBackendSummary(json.mock_llm_backend);
      })
      .catch((error: Error) => {
        dispatch({ type: "error.set", error: `Could not load API config: ${error.message}` });
      });
  }, []);

  useEffect(() => {
    return () => {
      window.speechSynthesis.cancel();
      recognitionRef.current?.stop();
    };
  }, []);

  const statusClass = useMemo(() => {
    if (state.status === "error") return `${styles.dot} ${styles.error}`;
    if (state.status === "speaking") return `${styles.dot} ${styles.speaking}`;
    if (state.status === "listening") return `${styles.dot} ${styles.ok}`;
    return styles.dot;
  }, [state.status]);

  async function requestMicrophone() {
    try {
      await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      setMicPermission("granted");
      return true;
    } catch (error) {
      setMicPermission("denied");
      dispatch({
        type: "error.set",
        error: error instanceof Error ? error.message : "Microphone permission was denied.",
      });
      return false;
    }
  }

  async function startSession() {
    if (!consent) {
      dispatch({
        type: "error.set",
        error: "Please confirm the cloud-processing consent before starting.",
      });
      return;
    }
    const allowed = await requestMicrophone();
    if (!allowed) return;

    const response = await fetch(`${API_BASE}/v1/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consent, mode }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      dispatch({ type: "error.set", error: body.detail ?? "Could not start session." });
      return;
    }
    const session = (await response.json()) as SessionResponse;
    dispatch({ type: "session.started", sessionId: session.session_id });

    if (session.mode === "livekit") {
      await connectLiveKit(session);
      return;
    }
    startBrowserRecognition();
  }

  async function connectLiveKit(session: SessionResponse) {
    try {
      const livekit = await import("livekit-client");
      const room = new livekit.Room();
      roomRef.current = room;
      room.on(livekit.RoomEvent.Connected, () => {
        setLiveKitSummary(`Connected to ${session.livekit_room}`);
        dispatch({ type: "status.set", status: "listening" });
      });
      room.on(livekit.RoomEvent.Disconnected, () => {
        setLiveKitSummary("Disconnected");
        const activeSessionId = stateRef.current.sessionId;
        if (activeSessionId) {
          void fetch(`${API_BASE}/v1/session/${activeSessionId}`, { method: "DELETE" }).catch(() => undefined);
        }
        dispatch({ type: "session.ended" });
      });
      room.on(livekit.RoomEvent.TrackSubscribed, async () => {
        dispatch({ type: "status.set", status: "speaking" });
        try {
          await room.startAudio();
        } catch {
          setLiveKitSummary("Connected. Tap the page once if autoplay is blocked.");
        }
      });
      await room.connect(session.livekit_url ?? "", session.livekit_token ?? "");
      await room.localParticipant.setMicrophoneEnabled(true);
      setLiveKitSummary(`Connected as ${session.livekit_identity}`);
    } catch (error) {
      dispatch({
        type: "error.set",
        error: error instanceof Error ? error.message : "LiveKit connection failed.",
      });
    }
  }

  function startBrowserRecognition() {
    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Recognition) {
      setLiveKitSummary("Browser speech recognition unavailable. Use the manual transcript box in mock mode.");
      return;
    }
    recognitionRef.current?.stop();
    const recognition = new Recognition();
    recognition.lang = "hi-IN";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onresult = async (event) => {
      const parts = Array.from(event.results)
        .map((entry) => entry[0]?.transcript ?? "")
        .filter(Boolean);
      const finalText = parts.join(" ").trim();
      if (finalText) {
        await handleTranscript({ finalText });
      }
    };
    recognition.onerror = (event) => {
      dispatch({ type: "error.set", error: `Speech recognition error: ${event.error}` });
    };
    recognition.onend = () => {
      const currentState = stateRef.current;
      if (currentState.sessionId && currentState.status !== "speaking") {
        dispatch({ type: "status.set", status: "listening" });
      }
    };
    recognitionRef.current = recognition;
    dispatch({ type: "status.set", status: "listening" });
    recognition.start();
  }

  async function handleTranscript(result: RecognitionResult) {
    const sessionId = stateRef.current.sessionId;
    if (!sessionId) return;
    const transcript = result.finalText.trim();
    if (!transcript) return;

    cancelCurrentSpeech();
    dispatch({ type: "transcript.add", entry: { id: makeId(), role: "user", text: transcript } });
    dispatch({ type: "status.set", status: "thinking" });

    const turnId = ++turnCounterRef.current;
    const requestAbortController = new AbortController();
    speechAbortRef.current = requestAbortController;

    const response = await fetch(`${API_BASE}/v1/mock/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: requestAbortController.signal,
      body: JSON.stringify({
        session_id: sessionId,
        transcript,
      }),
    }).catch((error: Error) => {
      if (error.name === "AbortError") {
        return null;
      }
      throw error;
    });

    if (!response) {
      return;
    }
    if (speechAbortRef.current !== requestAbortController || turnCounterRef.current !== turnId) {
      return;
    }

    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }));
      dispatch({ type: "error.set", error: body.detail ?? "Mock reply failed." });
      return;
    }

    const json = (await response.json()) as MockReplyResponse;
    if (speechAbortRef.current !== requestAbortController || turnCounterRef.current !== turnId) {
      return;
    }
    setBackendSummary(json.backend);
    dispatch({ type: "transcript.add", entry: { id: makeId(), role: "assistant", text: json.reply_text } });
    dispatch({ type: "status.set", status: "speaking" });
    await speakChunks(json.chunks, requestAbortController, turnId);
    if (speechAbortRef.current === requestAbortController && turnCounterRef.current === turnId) {
      dispatch({ type: "status.set", status: "listening" });
    }
  }

  async function speakChunks(chunks: string[], requestAbortController: AbortController, turnId: number) {
    if (stateRef.current.isMuted) {
      return;
    }
    for (const chunk of chunks) {
      if (speechAbortRef.current !== requestAbortController || turnCounterRef.current !== turnId) {
        return;
      }
      await new Promise<void>((resolve) => {
        const utterance = new SpeechSynthesisUtterance(chunk);
        activeUtterances.current.push(utterance);
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.onend = () => resolve();
        utterance.onerror = () => resolve();
        window.speechSynthesis.speak(utterance);
      });
    }
  }

  function cancelCurrentSpeech() {
    speechAbortRef.current?.abort();
    speechAbortRef.current = null;
    turnCounterRef.current += 1;
    activeUtterances.current = [];
    window.speechSynthesis.cancel();
  }

  async function stopSession() {
    cancelCurrentSpeech();
    recognitionRef.current?.stop();
    const maybeRoom = roomRef.current as { disconnect?: () => Promise<void> | void } | null;
    if (maybeRoom?.disconnect) {
      await maybeRoom.disconnect();
      roomRef.current = null;
    }
    const activeSessionId = stateRef.current.sessionId;
    if (activeSessionId) {
      await fetch(`${API_BASE}/v1/session/${activeSessionId}`, { method: "DELETE" }).catch(() => undefined);
    }
    dispatch({ type: "session.ended" });
  }

  async function submitManualTranscript() {
    if (!manualTranscript.trim()) return;
    await handleTranscript({ finalText: manualTranscript });
    setManualTranscript("");
  }

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <section className={styles.hero}>
          <div className={styles.badges}>
            <span className={styles.badge}>Next.js web UI</span>
            <span className={styles.badge}>FastAPI session API</span>
            <span className={styles.badge}>Mock + LiveKit-ready modes</span>
          </div>
          <h1>Hythere</h1>
          <p>
            A warm Hindi/Hinglish AI companion MVP. It is an AI, not a human, therapist, or
            emergency service. By default, transcripts stay only in memory and can be cleared from
            this page.
          </p>
          <div className={styles.status} aria-live="polite">
            <span className={statusClass} />
            {statusLabel(state.status)}
          </div>
        </section>

        <section className={styles.grid}>
          <div className={styles.panel}>
            <div className={styles.sectionTitle}>Start a session</div>
            <div className={styles.stack}>
              <label className={styles.inlineCheckbox}>
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                />
                <span>
                  I understand my audio or transcript may leave this device for cloud processing in
                  live mode or server-backed mock mode.
                </span>
              </label>

              <label className={styles.field}>
                <span className={styles.label}>Mode</span>
                <select
                  className={styles.select}
                  value={mode}
                  onChange={(event) => setMode(event.target.value as "mock" | "livekit")}
                >
                  <option value="mock">Mock / local demo</option>
                  <option value="livekit" disabled={!config?.livekit_enabled}>
                    LiveKit room
                  </option>
                </select>
              </label>

              <div className={styles.buttons}>
                <button className={styles.button} onClick={() => void startSession()}>
                  Start
                </button>
                <button className={styles.buttonSecondary} onClick={() => void stopSession()}>
                  End
                </button>
                <button className={styles.buttonGhost} onClick={() => dispatch({ type: "mute.toggle" })}>
                  {state.isMuted ? "Unmute" : "Mute"}
                </button>
                <button className={styles.buttonGhost} onClick={startBrowserRecognition}>
                  Listen again
                </button>
              </div>

              <div className={styles.metaGrid}>
                <div className={styles.metaCard}>
                  <div className={styles.metaLabel}>Mic permission</div>
                  <div className={styles.metaValue}>{micPermission}</div>
                </div>
                <div className={styles.metaCard}>
                  <div className={styles.metaLabel}>Backend</div>
                  <div className={styles.metaValue}>{backendSummary}</div>
                </div>
                <div className={styles.metaCard}>
                  <div className={styles.metaLabel}>Room status</div>
                  <div className={styles.metaValue}>{liveKitSummary}</div>
                </div>
                <div className={styles.metaCard}>
                  <div className={styles.metaLabel}>Session</div>
                  <div className={styles.metaValue}>{state.sessionId ?? "Not started"}</div>
                </div>
              </div>

              <label className={styles.inlineCheckbox}>
                <input
                  type="checkbox"
                  checked={showTranscript}
                  onChange={(event) => setShowTranscript(event.target.checked)}
                />
                <span>Show transcript on screen for this browser tab</span>
              </label>

              <label className={styles.field}>
                <span className={styles.label}>Manual transcript fallback</span>
                <textarea
                  className={styles.textarea}
                  value={manualTranscript}
                  onChange={(event) => setManualTranscript(event.target.value)}
                  placeholder="If browser speech recognition is unavailable, type what you said here in Hindi or Hinglish."
                />
              </label>
              <div className={styles.buttons}>
                <button className={styles.buttonSecondary} onClick={() => void submitManualTranscript()}>
                  Send manual turn
                </button>
                <button className={styles.buttonGhost} onClick={() => dispatch({ type: "transcript.clear" })}>
                  Clear transcript
                </button>
              </div>
              {state.error ? <div className={styles.errorText}>{state.error}</div> : null}
            </div>
          </div>

          <div className={styles.helpPanel}>
            <div className={styles.sectionTitle}>Simple testing notes</div>
            <ul className={styles.list}>
              <li>Mock mode works without API keys and is clearly labeled.</li>
              <li>LiveKit mode stays disabled until the backend has valid LiveKit credentials.</li>
              <li>Browser STT/TTS is a demo helper only; it does not verify live Sarvam STT/TTS quality.</li>
              <li>Use Chrome or Edge first for easier microphone and speech support.</li>
              <li>If audio does not autoplay, click once on the page and try again.</li>
            </ul>
            <div className={styles.notice}>
              Full server-hosted VAD/STT/TTS still requires valid provider credentials and a long-running
              worker. The API exposes the exact session and token boundaries for that path.
            </div>
            {!config?.distress_resource_configured ? (
              <div className={styles.warning}>
                Distress resource contact is not configured yet. Set verified regional crisis details on
                the server before any public deployment.
              </div>
            ) : null}
          </div>
        </section>

        {showTranscript ? (
          <section className={styles.logPanel}>
            <div className={styles.sectionTitle}>Ephemeral transcript</div>
            <ul className={styles.logList}>
              {state.transcript.length === 0 ? (
                <li className={styles.logItem}>Nothing yet. Start a session and speak or use the manual box.</li>
              ) : (
                state.transcript.map((entry) => (
                  <li className={styles.logItem} key={entry.id}>
                    <div className={styles.logRole}>{entry.role}</div>
                    <div>{entry.text}</div>
                  </li>
                ))
              )}
            </ul>
          </section>
        ) : null}
      </div>
    </main>
  );
}
