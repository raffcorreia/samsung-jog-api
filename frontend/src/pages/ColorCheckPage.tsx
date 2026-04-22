/**
 * Color and edge validation page — Phase 19.
 *
 * Full-screen panel for verifying the Waveshare 7-inch DSI panel:
 *   - Solid color swatches (red, green, blue, white, black, gray)
 *   - Horizontal grayscale gradient band
 *   - Small-text readability sample
 *   - 1px edge lines at top, bottom, left, and right to confirm panel alignment/cropping
 *
 * Tap/click anywhere or press Escape to exit back to Settings.
 */
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import styles from "./ColorCheckPage.module.css";

const SWATCHES = [
  { label: "Red", bg: "#ff0000", fg: "#ffffff" },
  { label: "Green", bg: "#00aa00", fg: "#ffffff" },
  { label: "Blue", bg: "#0044ff", fg: "#ffffff" },
  { label: "White", bg: "#ffffff", fg: "#000000" },
  { label: "Black", bg: "#000000", fg: "#ffffff" },
  { label: "Gray 50%", bg: "#808080", fg: "#ffffff" },
] as const;

const TEXT_SAMPLE = "The quick brown fox jumps over the lazy dog · 0123456789 · Aa Bb Cc Dd";

const TEXT_SIZES = [
  { label: "0.70rem", cls: "sz1" },
  { label: "0.85rem", cls: "sz2" },
  { label: "1.00rem", cls: "sz3" },
  { label: "1.20rem", cls: "sz4" },
  { label: "1.50rem", cls: "sz5" },
  { label: "1.90rem", cls: "sz6" },
] as const;

export function ColorCheckPage() {
  const navigate = useNavigate();

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") navigate(-1);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);

  return (
    /* Outer container: fills entire viewport, handles tap-to-exit */
    <div
      className={styles.page}
      data-testid="color-check-page"
      onClick={() => navigate(-1)}
    >
      {/* Edge lines */}
      <div className={styles.edgeTop} aria-hidden="true" />
      <div className={styles.edgeBottom} aria-hidden="true" />
      <div className={styles.edgeLeft} aria-hidden="true" />
      <div className={styles.edgeRight} aria-hidden="true" />

      <div className={styles.inner} onClick={(e) => e.stopPropagation()}>
        {/* Instruction */}
        <p className={styles.hint} data-testid="color-check-hint">
          Tap anywhere outside this panel to exit · Esc to exit
        </p>

        {/* Color swatches */}
        <div className={styles.swatchGrid}>
          {SWATCHES.map((s) => (
            <div
              key={s.label}
              className={styles.swatch}
              style={{ background: s.bg, color: s.fg }}
              data-testid={`swatch-${s.label.toLowerCase().replace(/\s+/g, "-")}`}
            >
              <span className={styles.swatchLabel}>{s.label}</span>
            </div>
          ))}
        </div>

        {/* Grayscale gradient band */}
        <div className={styles.gradientBand} aria-label="Grayscale gradient" />
        <div className={styles.gradientSteps} aria-label="Grayscale steps">
          {Array.from({ length: 9 }, (_, i) => {
            const v = Math.round((i / 8) * 255);
            return (
              <div
                key={v}
                className={styles.gradientStep}
                style={{
                  background: `rgb(${v},${v},${v})`,
                  color: v > 127 ? "#000" : "#fff",
                }}
              >
                {v}
              </div>
            );
          })}
        </div>

        {/* Readability samples — one row per size so you can identify the smallest legible size */}
        <div className={styles.readabilitySample} data-testid="readability-sample">
          {TEXT_SIZES.map(({ label, cls }) => (
            <div key={label} className={styles.sizeRow}>
              <span className={styles.sizeLabel}>{label}</span>
              <span className={styles[cls]}>{TEXT_SAMPLE}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
