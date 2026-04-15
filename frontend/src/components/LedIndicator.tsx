import styles from "./LedIndicator.module.css";

/**
 * KEY_LED status indicator — small circle overlaid on the JogPad area.
 * Gray = LED off / unknown. Blue = LED on.
 *
 * Phase 13: always stubbed to off (on=false). Phase 15 wires up real KEY_LED events.
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
