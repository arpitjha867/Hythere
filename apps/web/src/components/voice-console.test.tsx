import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { VoiceConsole } from "./voice-console";

class MockRecognition {
  continuous = false;
  interimResults = false;
  lang = "";
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  start = vi.fn();
  stop = vi.fn();
}

const mockRoom = {
  localParticipant: {
    setMicrophoneEnabled: vi.fn().mockResolvedValue(undefined),
  },
  connect: vi.fn().mockResolvedValue(undefined),
  on: vi.fn(),
  startAudio: vi.fn().mockResolvedValue(undefined),
};

vi.mock("livekit-client", () => ({
  Room: vi.fn(() => mockRoom),
  RoomEvent: {
    Connected: "connected",
    Disconnected: "disconnected",
    TrackSubscribed: "trackSubscribed",
  },
}));

describe("VoiceConsole", () => {
  let recognition: MockRecognition;

  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    recognition = new MockRecognition();
    vi.restoreAllMocks();
    mockRoom.localParticipant.setMicrophoneEnabled.mockClear();
    mockRoom.connect.mockClear();
    mockRoom.on.mockClear();
    mockRoom.startAudio.mockClear();
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              mock_enabled: true,
              livekit_enabled: false,
              local_dev_auth_enabled: true,
              max_session_minutes: 20,
              max_concurrent_sessions: 20,
              distress_resource_configured: false,
              mock_llm_backend: "mock",
              livekit_url: null,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        )
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              session_id: "session_test",
              mode: "mock",
              expires_in_seconds: 1200,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        ),
    );
    Object.defineProperty(window, "webkitSpeechRecognition", {
      configurable: true,
      value: vi.fn(() => recognition),
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({}),
      },
    });
  });

  it("restarts recognition after a turn ends while the session stays active", async () => {
    render(<VoiceConsole />);

    fireEvent.click(
      await screen.findByLabelText(
        "I understand my audio or transcript may leave this device for cloud processing in live mode or server-backed mock mode.",
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Start" }));

    await waitFor(() => expect(recognition.start).toHaveBeenCalledTimes(1));

    recognition.onend?.();

    await waitFor(() => expect(recognition.start).toHaveBeenCalledTimes(2));
  });

  it("shows recognition errors in the UI", async () => {
    render(<VoiceConsole />);

    fireEvent.click(
      await screen.findByLabelText(
        "I understand my audio or transcript may leave this device for cloud processing in live mode or server-backed mock mode.",
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Start" }));

    await waitFor(() => expect(recognition.start).toHaveBeenCalledTimes(1));

    recognition.onerror?.({ error: "network" });

    expect(await screen.findByText("Speech recognition error: network")).toBeTruthy();
  });

  it("keeps manual transcript controls out of the mock path during a LiveKit session", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              mock_enabled: true,
              livekit_enabled: true,
              local_dev_auth_enabled: true,
              max_session_minutes: 20,
              max_concurrent_sessions: 20,
              distress_resource_configured: false,
              mock_llm_backend: "mock",
              livekit_url: "wss://example.livekit.cloud",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        )
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              session_id: "session_livekit",
              mode: "livekit",
              expires_in_seconds: 1200,
              livekit_url: "wss://example.livekit.cloud",
              livekit_room: "room-1",
              livekit_identity: "user-1",
              livekit_token: "token-1",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        ),
    );

    render(<VoiceConsole />);

    fireEvent.click(
      await screen.findByLabelText(
        "I understand my audio or transcript may leave this device for cloud processing in live mode or server-backed mock mode.",
      ),
    );
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "livekit" } });
    fireEvent.click(screen.getByRole("button", { name: "Start" }));

    await waitFor(() => expect(mockRoom.connect).toHaveBeenCalledTimes(1));

    const textarea = screen.getByPlaceholderText(
      "If browser speech recognition is unavailable, type what you said here in Hindi or Hinglish.",
    ) as HTMLTextAreaElement;
    expect(textarea.disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Send manual turn" }) as HTMLButtonElement).disabled).toBe(true);
    expect((fetch as ReturnType<typeof vi.fn>).mock.calls).toHaveLength(2);
  });
});
