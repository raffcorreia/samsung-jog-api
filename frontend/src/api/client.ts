import type { CommandRejectedBody, JogAction, LogLevel, StatusPayload } from "../types";

function apiBase(): string {
  const v = import.meta.env.VITE_API_BASE;
  if (typeof v === "string" && v.length > 0) {
    return v.replace(/\/$/, "");
  }
  return "";
}

export async function fetchStatus(): Promise<StatusPayload> {
  const r = await fetch(`${apiBase()}/api/v1/status`);
  if (!r.ok) {
    throw new Error(`status ${r.status}`);
  }
  return (await r.json()) as StatusPayload;
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
