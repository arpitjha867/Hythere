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

describe("VoiceConsole", () => {
  let recognition: MockRecognition;

  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    recognition = new MockRecognition();
    vi.restoreAllMocks();
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
});
