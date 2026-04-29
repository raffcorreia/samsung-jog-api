/**
 * KEY_LED status indicator — flat SVG circle, no gradients (avoid banding at small sizes).
 * Gray = off, blue = on, driven by ``status.signals.key_led_active`` / ``bus/led_changed``.
 */
export function LedIndicator({ on }: { on: boolean }) {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 28 28"
      role="status"
      aria-label={on ? "LED on" : "LED off"}
      data-testid="led-indicator"
      data-led={on ? "on" : "off"}
      style={{
        display: "block",
        flexShrink: 0,
        filter: on ? "drop-shadow(0 0 5px #6cb6ff) drop-shadow(0 0 10px rgba(108,182,255,0.5))" : "none",
        transition: "filter 0.3s ease",
      }}
    >
      {/* Body */}
      <circle
        cx="14" cy="14" r="12"
        fill={on ? "#4a9ede" : "#555e69"}
        stroke={on ? "rgba(108,182,255,0.4)" : "rgba(232,238,244,0.12)"}
        strokeWidth="1"
      />
      {/* Specular highlight */}
      <ellipse cx="10.5" cy="9" rx="4" ry="2.5" fill="rgba(255,255,255,0.28)" />
    </svg>
  );
}
