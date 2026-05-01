import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchDisplayBrightness, fetchLedBrightness, fetchNetworkInfo, fetchStatus, setDisplayBrightness, setLedBrightness } from "../api/client";
import type { NetworkInfo } from "../api/client";
import { DECK_WIDGETS } from "../widgets/deckWidgets";
import styles from "./SettingsPage.module.css";

function VersionPanel() {
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    fetchStatus()
      .then((s) => setVersion(s.version))
      .catch(() => { /* non-critical */ });
  }, []);

  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>Version</h2>
      <div className={styles.row}>
        <span className={styles.rowLabel}>pi-deck</span>
        <span className={styles.rowValue}>{version ?? "—"}</span>
      </div>
    </section>
  );
}

function NetworkPanel() {
  const [info, setInfo] = useState<NetworkInfo | null>(null);

  useEffect(() => {
    fetchNetworkInfo()
      .then(setInfo)
      .catch(() => { /* non-critical */ });
  }, []);

  if (!info) return null;

  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>Network</h2>
      <div className={styles.row}>
        <span className={styles.rowLabel}>Hostname</span>
        <span className={styles.rowValue}>{info.hostname}</span>
      </div>
      {info.interfaces.map((iface) => (
        <div className={styles.row} key={iface.name}>
          <span className={styles.rowLabel}>
            <span
              className={iface.connected ? styles.dotOn : styles.dotOff}
              aria-hidden="true"
            />
            {iface.name}
          </span>
          <span className={styles.rowValue}>{iface.ip ?? "—"}</span>
        </div>
      ))}
    </section>
  );
}

/** Debounce helper — only the last call within ``delay`` ms fires. */
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

function BrightnessSlider() {
  const [pct, setPct] = useState<number | null>(null);
  const debouncedPct = useDebounce(pct, 250);
  const lastSentRef = useRef<number | null>(null);

  // Load initial brightness from backend.
  useEffect(() => {
    fetchDisplayBrightness()
      .then((b) => setPct(b.brightness_pct))
      .catch(() => {
        /* non-critical; slider starts empty until load succeeds */
      });
  }, []);

  // Send debounced value to backend.
  useEffect(() => {
    if (debouncedPct === null) return;
    if (debouncedPct === lastSentRef.current) return;
    lastSentRef.current = debouncedPct;
    setDisplayBrightness(debouncedPct).catch(() => {});
  }, [debouncedPct]);

  const displayPct = pct ?? 0;

  return (
    <div className={styles.sliderRow}>
      <div className={styles.sliderLabel}>
        <span>Brightness</span>
        <span className={styles.sliderValue} data-testid="brightness-value">
          {pct === null ? "—" : `${displayPct}%`}
        </span>
      </div>
      <input
        className={styles.slider}
        type="range"
        min={0}
        max={100}
        step={1}
        value={displayPct}
        disabled={pct === null}
        aria-label="Display brightness"
        data-testid="brightness-slider"
        onChange={(e) => setPct(Number(e.target.value))}
      />
      <p className={styles.sliderNote}>
        Full 0–100% range is available. On Raspberry Pi 2 the safe ceiling was 170/255 due to
        power-path limitations; Raspberry Pi 5 is stable at full brightness.
      </p>
    </div>
  );
}

function LedBrightnessSlider() {
  const [pct, setPct] = useState<number | null>(null);
  const debouncedPct = useDebounce(pct, 250);
  const lastSentRef = useRef<number | null>(null);

  useEffect(() => {
    fetchLedBrightness()
      .then((b) => setPct(b.brightness_pct))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (debouncedPct === null) return;
    if (debouncedPct === lastSentRef.current) return;
    lastSentRef.current = debouncedPct;
    setLedBrightness(debouncedPct).catch(() => {});
  }, [debouncedPct]);

  const displayPct = pct ?? 0;

  return (
    <div className={styles.sliderRow}>
      <div className={styles.sliderLabel}>
        <span>Status LED brightness</span>
        <span className={styles.sliderValue} data-testid="led-brightness-value">
          {pct === null ? "—" : `${displayPct}%`}
        </span>
      </div>
      <input
        className={styles.slider}
        type="range"
        min={0}
        max={100}
        step={1}
        value={displayPct}
        disabled={pct === null}
        aria-label="Status LED brightness"
        data-testid="led-brightness-slider"
        onChange={(e) => setPct(Number(e.target.value))}
      />
    </div>
  );
}

/**
 * Settings page — Phase 19 adds brightness slider and color-check entry.
 */
export function SettingsPage() {
  const navigate = useNavigate();

  return (
    <div className={styles.page} data-widget={DECK_WIDGETS.settings}>
      <VersionPanel />
      <NetworkPanel />
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Appearance</h2>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Theme</span>
          <span className={styles.rowValue}>Dark</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Show live log</span>
          <span className={styles.rowValue}>On</span>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Display</h2>
        <div className={styles.row} style={{ flexDirection: "column", alignItems: "stretch" }}>
          <BrightnessSlider />
        </div>
        <div className={styles.row} style={{ flexDirection: "column", alignItems: "stretch" }}>
          <LedBrightnessSlider />
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Color &amp; edge validation</span>
          <button
            className={styles.actionBtn}
            type="button"
            data-testid="open-color-check"
            onClick={() => navigate("/color-check")}
          >
            Open
          </button>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Control</h2>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Default operating mode</span>
          <span className={styles.rowValue}>JOG</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Hardware mode</span>
          <span className={styles.rowValue}>Live</span>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>About</h2>
        <div className={styles.row}>
          <span className={styles.rowLabel}>pi-deck</span>
          <span className={styles.rowValue}>Settings coming in a future phase</span>
        </div>
      </section>
    </div>
  );
}
