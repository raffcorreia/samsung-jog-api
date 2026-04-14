import type { WsEventV1 } from "../types";

/** Human-readable line for the live log panel (mirrors websocket activity). */
export function formatWsEventLine(ev: WsEventV1): string {
  if (ev.category === "control" && ev.type === "connected") {
    const st = ev.data.status as { hardware?: string; control_state?: string } | undefined;
    const hw = st?.hardware ?? "?";
    const cs = st?.control_state ?? "?";
    return `connected — hardware=${hw} control=${cs}`;
  }
  if (ev.category === "command" && ev.type === "hold_started") {
    const action = String(ev.data.action ?? "?");
    return `hold — ${action}`;
  }
  if (ev.category === "command" && ev.type === "accepted") {
    const action = String(ev.data.action ?? "?");
    const ms = Number(ev.data.duration_ms ?? 0);
    return `command ok — ${action} ${ms}ms`;
  }
  if (ev.category === "command" && ev.type === "rejected") {
    const reason = String(ev.data.reason ?? "?");
    const msg = String(ev.data.message ?? "");
    return `command rejected — ${reason}: ${msg}`;
  }
  if (ev.category === "control" && ev.type === "state") {
    const cs = String(ev.data.control_state ?? "?");
    const om = String(ev.data.operating_mode ?? "?");
    return `control — state=${cs} mode=${om}`;
  }
  if (ev.category === "bus" && ev.type === "snapshot") {
    const a1 = Boolean(ev.data.key_adc1_active);
    const led = Boolean(ev.data.key_led_active);
    return `signals — adc1_active=${a1} key_led_active=${led}`;
  }
  return `${ev.category}/${ev.type}`;
}
