import type { CommandRejectedBody, JogAction, StatusPayload } from "../types";

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

export type JogDownResult =
  | { ok: true; hold_token: string }
  | { ok: false; body: CommandRejectedBody };

/** Physical hold: assert until matching :func:`jogUp` with the returned ``hold_token``. */
export async function jogDown(action: JogAction): Promise<JogDownResult> {
  const r = await fetch(`${apiBase()}/api/v1/jog/down`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  if (r.status === 200) {
    const j = (await r.json()) as { ok?: boolean; hold_token?: string };
    const hold_token = j.hold_token;
    if (typeof hold_token !== "string" || hold_token.length < 8) {
      throw new Error("jog down missing hold_token");
    }
    return { ok: true, hold_token };
  }
  if (r.status === 409) {
    return { ok: false, body: (await r.json()) as CommandRejectedBody };
  }
  if (r.status === 422) {
    throw new Error("invalid jog request");
  }
  throw new Error(`jog down failed: ${r.status}`);
}

export type JogUpResult =
  | { ok: true; duration_ms: number }
  | { ok: false; body: CommandRejectedBody };

export async function jogUp(holdToken: string): Promise<JogUpResult> {
  const r = await fetch(`${apiBase()}/api/v1/jog/up`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hold_token: holdToken }),
  });
  if (r.status === 200) {
    const j = (await r.json()) as { ok: boolean; duration_ms: number };
    return { ok: true, duration_ms: j.duration_ms ?? 0 };
  }
  if (r.status === 409) {
    return { ok: false, body: (await r.json()) as CommandRejectedBody };
  }
  throw new Error(`jog up failed: ${r.status}`);
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
