import type { SignalSnapshot } from "../types";

/** Must stay aligned with ``live_log._bus_snapshot_log_message`` (Python). */
export function formatBusSnapshotLogMessage(s: SignalSnapshot): string {
  const k2 = s.key_adc2_direction;
  const k2s = k2 === null || k2 === undefined ? "null" : k2;
  return `key_adc1_active=${s.key_adc1_active ? "true" : "false"} key_adc2_direction=${k2s} key_led_active=${s.key_led_active ? "true" : "false"}`;
}

/** Aligned with ``_event_message`` for ``bus/led_changed`` in live_log.py. */
export function formatBusLedLogMessage(keyLedActive: boolean): string {
  return `key_led -> ${keyLedActive ? "on" : "off"}`;
}
