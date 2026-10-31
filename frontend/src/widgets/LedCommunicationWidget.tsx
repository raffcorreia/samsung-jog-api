import { useEffect, useMemo, useRef, useState } from "react";

import {
  clearLedCommunication,
  ledCommunicationExportUrl,
  replayLedCommunication,
  startLedCommunication,
  stopLedCommunication,
} from "../api/client";
import type { LedCommunicationState, LedCommunicationStatus } from "../types";
import { DECK_WIDGETS } from "./deckWidgets";
import styles from "./LedCommunicationWidget.module.css";

const WIDTH = 900;
const HEIGHT = 170;

function milliseconds(ns: number | null): string {
  return ns === null ? "—" : `${(ns / 1_000_000).toFixed(ns < 10_000_000 ? 2 : 1)} ms`;
}

export function LedCommunicationWidget({ state }: { state: LedCommunicationState }) {
  const [localStatus, setLocalStatus] = useState<LedCommunicationStatus | null>(state.status);
  const [error, setError] = useState<string | null>(null);
  const replayRef = useRef<HTMLInputElement>(null);

  useEffect(() => setLocalStatus(state.status), [state.status]);
  const status = localStatus ?? state.status;

  const path = useMemo(() => {
    const edges = state.edges;
    if (edges.length === 0) return "";
    const start = edges[0].monotonic_ns;
    const end = edges[edges.length - 1].monotonic_ns;
    const span = Math.max(1, end - start);
    let level = edges[0].level;
    let d = `M 0 ${level ? 30 : 140}`;
    for (const edge of edges) {
      const x = ((edge.monotonic_ns - start) / span) * WIDTH;
      d += ` H ${x.toFixed(2)} V ${edge.level ? 30 : 140}`;
      level = edge.level;
    }
    d += ` H ${WIDTH}`;
    return d;
  }, [state.edges]);

  const run = async (action: () => Promise<LedCommunicationStatus>) => {
    setError(null);
    try {
      setLocalStatus(await action());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const frame = status?.latest_frame;

  return (
    <section className={styles.widget} data-widget={DECK_WIDGETS.ledCommunication} data-testid="led-communication-monitor">
      <header className={styles.header}>
        <div>
          <h2>Monitor LED communication</h2>
          <p>1007.7 · 10 ms biphase-mark · STATE frames</p>
        </div>
        <div className={styles.liveState} data-capturing={status?.capturing ? "true" : "false"}>
          <span />{status?.capturing ? "CAPTURING" : "STOPPED"}
        </div>
      </header>

      <div className={styles.waveform} aria-label="Raw KEY_LED waveform">
        <div className={styles.axisTop}>physical 1</div>
        <div className={styles.axisBottom}>physical 0</div>
        {path ? (
          <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" role="img">
            <path d={path} />
          </svg>
        ) : (
          <div className={styles.empty}>Waiting for raw KEY_LED edges…</div>
        )}
      </div>

      <div className={styles.metrics}>
        <Metric label="Level" value={status?.level === null || status?.level === undefined ? "—" : String(status.level)} />
        <Metric label="Edges" value={String(status?.accepted_edges ?? 0)} />
        <Metric label="Median" value={milliseconds(status?.intervals.median_ns ?? null)} />
        <Metric label="Range" value={`${milliseconds(status?.intervals.min_ns ?? null)} – ${milliseconds(status?.intervals.max_ns ?? null)}`} />
        <Metric label="Glitches" value={String(status?.rejected_glitches ?? 0)} warn={Boolean(status?.rejected_glitches)} />
        <Metric label="Overruns" value={String(status?.overruns ?? 0)} warn={Boolean(status?.overruns)} />
      </div>

      <div className={styles.framePanel}>
        <div>
          <span className={styles.eyebrow}>Latest validated STATE frame</span>
          {frame ? (
            <strong>#{frame.sequence} · {frame.layout.toUpperCase()} · {frame.input1.toUpperCase()} / {frame.input2.toUpperCase()}</strong>
          ) : (
            <strong>No valid frame decoded</strong>
          )}
        </div>
        <code>{frame?.raw_hex ?? "ffff 2dd4 11 … crc"}</code>
        <div className={styles.frameCount}>{status?.valid_frames ?? 0} valid · {status?.missing_frames ?? 0} missing</div>
      </div>

      <footer className={styles.controls}>
        <button type="button" onClick={() => void run(status?.capturing ? stopLedCommunication : startLedCommunication)}>
          {status?.capturing ? "Stop" : "Start"}
        </button>
        <button type="button" onClick={() => void run(clearLedCommunication)}>Clear</button>
        <a href={ledCommunicationExportUrl()} download="key-led-capture.json">Export</a>
        <button type="button" onClick={() => replayRef.current?.click()}>Replay file</button>
        <input
          ref={replayRef}
          className={styles.hiddenInput}
          type="file"
          accept="application/json,.json"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (!file) return;
            void file.text().then(JSON.parse).then((document) => run(() => replayLedCommunication(document))).catch((e) => setError(String(e)));
          }}
        />
        <span className={styles.config}>half-bit {milliseconds(status?.half_bit_ns ?? null)} · tolerance {Math.round((status?.tolerance ?? 0) * 100)}%</span>
      </footer>
      {error && <div className={styles.error}>{error}</div>}
    </section>
  );
}

function Metric({ label, value, warn = false }: { label: string; value: string; warn?: boolean }) {
  return <div className={styles.metric} data-warn={warn ? "true" : "false"}><span>{label}</span><strong>{value}</strong></div>;
}
