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
