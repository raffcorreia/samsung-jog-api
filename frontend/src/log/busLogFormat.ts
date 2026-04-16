/** Aligned with ``_event_message`` for ``bus/led_changed`` in live_log.py. */
export function formatBusLedLogMessage(keyLedActive: boolean): string {
  return `key_led -> ${keyLedActive ? "on" : "off"}`;
}
