export type UiStatus = "idle" | "listening" | "thinking" | "speaking" | "error";

export interface TranscriptEntry {
  id: string;
  role: "user" | "assistant";
  text: string;
}

export interface VoiceState {
  status: UiStatus;
  sessionId: string | null;
  transcript: TranscriptEntry[];
  error: string | null;
  isMuted: boolean;
}

export type VoiceAction =
  | { type: "session.started"; sessionId: string }
  | { type: "session.ended" }
  | { type: "status.set"; status: UiStatus }
  | { type: "transcript.add"; entry: TranscriptEntry }
  | { type: "transcript.clear" }
  | { type: "mute.toggle" }
  | { type: "error.set"; error: string };

export const initialVoiceState: VoiceState = {
  status: "idle",
  sessionId: null,
  transcript: [],
  error: null,
  isMuted: false,
};

export function voiceReducer(state: VoiceState, action: VoiceAction): VoiceState {
  switch (action.type) {
    case "session.started":
      return {
        ...state,
        sessionId: action.sessionId,
        status: "listening",
        error: null,
      };
    case "session.ended":
      return {
        ...state,
        sessionId: null,
        status: "idle",
      };
    case "status.set":
      return {
        ...state,
        status: action.status,
      };
    case "transcript.add":
      return {
        ...state,
        transcript: [...state.transcript, action.entry],
      };
    case "transcript.clear":
      return {
        ...state,
        transcript: [],
      };
    case "mute.toggle":
      return {
        ...state,
        isMuted: !state.isMuted,
      };
    case "error.set":
      return {
        ...state,
        status: "error",
        error: action.error,
      };
    default:
      return state;
  }
}

export function statusLabel(status: UiStatus): string {
  if (status === "listening") return "Listening";
  if (status === "thinking") return "Thinking";
  if (status === "speaking") return "Speaking";
  if (status === "error") return "Needs attention";
  return "Idle";
}
