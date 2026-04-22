import type {
  CommandRejectedBody,
  JogAction,
  LogLevel,
  RecordingLibrary,
  RecordingRejectedBody,
  RecordingState,
  RecordingSummary,
  StatusPayload,
} from "../types";

function apiBase(): string {
  const v = import.meta.env.VITE_API_BASE;
  if (typeof v === "string" && v.length > 0) {
    return v.replace(/\/$/, "");
  }
  return "";
}

function normalizeStatusPayload(p: StatusPayload): StatusPayload {
  return {
    ...p,
    signals: {
      ...p.signals,
      key_adc2_direction: p.signals.key_adc2_direction ?? null,
    },
  };
}

export async function fetchStatus(): Promise<StatusPayload> {
  const r = await fetch(`${apiBase()}/api/v1/status`);
  if (!r.ok) {
    throw new Error(`status ${r.status}`);
  }
  const j = (await r.json()) as StatusPayload;
  return normalizeStatusPayload(j);
}

export type JogPressResult = { ok: true } | { ok: false; body: CommandRejectedBody };

export type JogHoldResult = { ok: true } | { ok: false; body: CommandRejectedBody };

/** Hold a direction until {@link releaseJog} is called with the same action. */
export async function jogHold(action: JogAction): Promise<JogHoldResult> {
  const r = await fetch(`${apiBase()}/api/v1/jog/hold`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  if (r.status === 200) {
    return { ok: true };
  }
  if (r.status === 409) {
    return { ok: false, body: (await r.json()) as CommandRejectedBody };
  }
  if (r.status === 422) {
    throw new Error("invalid jog request");
  }
  throw new Error(`jog hold failed: ${r.status}`);
}

export type JogReleaseResult =
  | { ok: true; duration_ms: number }
  | { ok: false; body: CommandRejectedBody };

export async function releaseJog(action: JogAction): Promise<JogReleaseResult> {
  const r = await fetch(`${apiBase()}/api/v1/jog/release`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  if (r.status === 200) {
    const j = (await r.json()) as { ok: boolean; duration_ms: number };
    return { ok: true, duration_ms: j.duration_ms ?? 0 };
  }
  if (r.status === 409) {
    return { ok: false, body: (await r.json()) as CommandRejectedBody };
  }
  throw new Error(`jog release failed: ${r.status}`);
}

/** Legacy one-shot timed assertion (scripts / tests). */
export async function jogPress(action: JogAction, durationMs: number): Promise<JogPressResult> {
  const r = await fetch(`${apiBase()}/api/v1/jog/press`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, duration_ms: durationMs }),
  });
  if (r.status === 200) {
    return { ok: true };
  }
  if (r.status === 409) {
    return { ok: false, body: (await r.json()) as CommandRejectedBody };
  }
  if (r.status === 422) {
    throw new Error("invalid jog request");
  }
  throw new Error(`jog press failed: ${r.status}`);
}

export async function postLogEntry(params: {
  level?: LogLevel;
  source: string;
  message: string;
}): Promise<void> {
  const r = await fetch(`${apiBase()}/api/v1/log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      level: params.level ?? "info",
      source: params.source,
      message: params.message,
    }),
  });
  if (!r.ok) {
    throw new Error(`log append failed: ${r.status}`);
  }
}

/** Remove all entries from the server-side live log buffer (broadcasts to websocket clients). */
export async function deleteLiveLog(): Promise<void> {
  const r = await fetch(`${apiBase()}/api/v1/log`, { method: "DELETE" });
  if (!r.ok) {
    throw new Error(`log clear failed: ${r.status}`);
  }
}

export type RecordingResult<T> = { ok: true; body: T } | { ok: false; body: RecordingRejectedBody };

export async function fetchRecordingLibrary(): Promise<RecordingLibrary> {
  const r = await fetch(`${apiBase()}/api/v1/recordings`);
  if (!r.ok) {
    throw new Error(`recordings ${r.status}`);
  }
  return (await r.json()) as RecordingLibrary;
}

export async function fetchRecordingState(): Promise<RecordingState> {
  const r = await fetch(`${apiBase()}/api/v1/recordings/state`);
  if (!r.ok) {
    throw new Error(`recording state ${r.status}`);
  }
  return (await r.json()) as RecordingState;
}

export async function startRecording(): Promise<RecordingResult<RecordingState>> {
  const r = await fetch(`${apiBase()}/api/v1/recordings/start`, { method: "POST" });
  if (r.status === 200) {
    return { ok: true, body: (await r.json()) as RecordingState };
  }
  if (r.status === 400 || r.status === 404 || r.status === 409) {
    return { ok: false, body: (await r.json()) as RecordingRejectedBody };
  }
  throw new Error(`recording start failed: ${r.status}`);
}

export async function stopRecording(): Promise<RecordingResult<{ ok: true; item: RecordingSummary }>> {
  const r = await fetch(`${apiBase()}/api/v1/recordings/stop`, { method: "POST" });
  if (r.status === 200) {
    return { ok: true, body: (await r.json()) as { ok: true; item: RecordingSummary } };
  }
  if (r.status === 400 || r.status === 404 || r.status === 409) {
    return { ok: false, body: (await r.json()) as RecordingRejectedBody };
  }
  throw new Error(`recording stop failed: ${r.status}`);
}

export async function playRecording(recordingId: string): Promise<RecordingResult<RecordingState>> {
  const r = await fetch(`${apiBase()}/api/v1/recordings/${encodeURIComponent(recordingId)}/play`, {
    method: "POST",
  });
  if (r.status === 200) {
    return { ok: true, body: (await r.json()) as RecordingState };
  }
  if (r.status === 400 || r.status === 404 || r.status === 409) {
    return { ok: false, body: (await r.json()) as RecordingRejectedBody };
  }
  throw new Error(`recording play failed: ${r.status}`);
}

export async function stopRecordingPlayback(): Promise<RecordingResult<RecordingState>> {
  const r = await fetch(`${apiBase()}/api/v1/recordings/stop-playback`, { method: "POST" });
  if (r.status === 200) {
    return { ok: true, body: (await r.json()) as RecordingState };
  }
  if (r.status === 400 || r.status === 404 || r.status === 409) {
    return { ok: false, body: (await r.json()) as RecordingRejectedBody };
  }
  throw new Error(`recording stop playback failed: ${r.status}`);
}

export async function renameRecording(
  recordingId: string,
  name: string,
): Promise<RecordingResult<{ ok: true; item: RecordingSummary }>> {
  const r = await fetch(`${apiBase()}/api/v1/recordings/${encodeURIComponent(recordingId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (r.status === 200) {
    return { ok: true, body: (await r.json()) as { ok: true; item: RecordingSummary } };
  }
  if (r.status === 400 || r.status === 404 || r.status === 409) {
    return { ok: false, body: (await r.json()) as RecordingRejectedBody };
  }
  throw new Error(`recording rename failed: ${r.status}`);
}

export async function deleteRecording(recordingId: string): Promise<RecordingResult<{ ok: true }>> {
  const r = await fetch(`${apiBase()}/api/v1/recordings/${encodeURIComponent(recordingId)}`, {
    method: "DELETE",
  });
  if (r.status === 200) {
    return { ok: true, body: (await r.json()) as { ok: true } };
  }
  if (r.status === 400 || r.status === 404 || r.status === 409) {
    return { ok: false, body: (await r.json()) as RecordingRejectedBody };
  }
  throw new Error(`recording delete failed: ${r.status}`);
}

export async function uploadRecording(file: File): Promise<RecordingResult<{ ok: true; item: RecordingSummary }>> {
  const body = new FormData();
  body.append("file", file);
  const r = await fetch(`${apiBase()}/api/v1/recordings/upload`, {
    method: "POST",
    body,
  });
  if (r.status === 200) {
    return { ok: true, body: (await r.json()) as { ok: true; item: RecordingSummary } };
  }
  if (r.status === 400 || r.status === 404 || r.status === 409) {
    return { ok: false, body: (await r.json()) as RecordingRejectedBody };
  }
  throw new Error(`recording upload failed: ${r.status}`);
}

export async function fetchRecordingContent(recordingId: string): Promise<string> {
  const r = await fetch(`${apiBase()}/api/v1/recordings/${encodeURIComponent(recordingId)}/content`);
  if (r.status === 200) {
    return await r.text();
  }
  throw new Error(`recording content fetch failed: ${r.status}`);
}

export async function updateRecordingContent(
  recordingId: string,
  content: string,
): Promise<RecordingResult<{ ok: true; item: RecordingSummary }>> {
  const r = await fetch(`${apiBase()}/api/v1/recordings/${encodeURIComponent(recordingId)}/content`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: content,
  });
  if (r.status === 200) {
    return { ok: true, body: (await r.json()) as { ok: true; item: RecordingSummary } };
  }
  if (r.status === 400 || r.status === 404 || r.status === 409) {
    return { ok: false, body: (await r.json()) as RecordingRejectedBody };
  }
  throw new Error(`recording content update failed: ${r.status}`);
}

export function recordingDownloadUrl(recordingId: string): string {
  return `${apiBase()}/api/v1/recordings/${encodeURIComponent(recordingId)}/download`;
}

// ── Phase 19: display brightness / power / shutdown ───────────────────────

export interface DisplayBrightness {
  brightness_pct: number;
  brightness_raw: number;
  max_raw: number;
}

export interface DisplayPower {
  on: boolean;
  brightness_pct: number;
}

export async function fetchDisplayBrightness(): Promise<DisplayBrightness> {
  const r = await fetch(`${apiBase()}/api/v1/display/brightness`);
  if (!r.ok) throw new Error(`display brightness fetch failed: ${r.status}`);
  return (await r.json()) as DisplayBrightness;
}

export async function setDisplayBrightness(brightnessPct: number): Promise<DisplayBrightness> {
  const r = await fetch(`${apiBase()}/api/v1/display/brightness`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brightness_pct: brightnessPct }),
  });
  if (!r.ok) throw new Error(`display brightness set failed: ${r.status}`);
  return (await r.json()) as DisplayBrightness;
}

export async function fetchDisplayPower(): Promise<DisplayPower> {
  const r = await fetch(`${apiBase()}/api/v1/display/power`);
  if (!r.ok) throw new Error(`display power fetch failed: ${r.status}`);
  return (await r.json()) as DisplayPower;
}

export async function setDisplayPower(on: boolean): Promise<DisplayPower> {
  const r = await fetch(`${apiBase()}/api/v1/display/power`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ on }),
  });
  if (!r.ok) throw new Error(`display power set failed: ${r.status}`);
  return (await r.json()) as DisplayPower;
}

export async function requestShutdown(): Promise<{ ok: boolean; message: string }> {
  const r = await fetch(`${apiBase()}/api/v1/system/shutdown`, { method: "POST" });
  if (!r.ok) throw new Error(`shutdown request failed: ${r.status}`);
  return (await r.json()) as { ok: boolean; message: string };
}

export function websocketEventsUrl(): string {
  const base = apiBase();
  if (base.startsWith("http://") || base.startsWith("https://")) {
    const u = new URL(base);
    const wsProto = u.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProto}//${u.host}/ws/events`;
  }
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/events`;
}
