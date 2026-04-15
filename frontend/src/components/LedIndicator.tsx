import styles from "./LedIndicator.module.css";

/**
 * KEY_LED status indicator — small circle overlaid on the JogPad area.
 * Gray = off, blue = on, driven by ``status.signals.key_led_active`` / ``bus/led_changed``.
 */
export function LedIndicator({ on }: { on: boolean }) {
  return (
    <div
      className={`${styles.indicator} ${on ? styles.on : styles.off}`}
      role="status"
      aria-label={on ? "LED on" : "LED off"}
      data-testid="led-indicator"
      data-led={on ? "on" : "off"}
    />
  );
}
