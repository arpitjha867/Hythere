import { describe, expect, it } from "vitest";
import { initialVoiceState, statusLabel, voiceReducer } from "./voice-state";

describe("voiceReducer", () => {
  it("starts a session and clears prior errors", () => {
    const state = voiceReducer(
      { ...initialVoiceState, error: "boom", status: "error" },
      { type: "session.started", sessionId: "session-1" },
    );

    expect(state.sessionId).toBe("session-1");
    expect(state.status).toBe("listening");
    expect(state.error).toBeNull();
  });

  it("appends transcript entries in order", () => {
    const afterUser = voiceReducer(initialVoiceState, {
      type: "transcript.add",
      entry: { id: "1", role: "user", text: "hello" },
    });
    const afterAssistant = voiceReducer(afterUser, {
      type: "transcript.add",
      entry: { id: "2", role: "assistant", text: "hi" },
    });

    expect(afterAssistant.transcript.map((entry) => entry.role)).toEqual(["user", "assistant"]);
  });

  it("maps user-facing status labels", () => {
    expect(statusLabel("idle")).toBe("Idle");
    expect(statusLabel("speaking")).toBe("Speaking");
  });
});
