import { useEffect, useMemo, useRef, useState } from "react";

import {
  clearLedCommunication,
  ledCommunicationExportUrl,
  replayLedCommunication,
  startLedCommunication,
  stopLedCommunication,
} from "../api/client";
import type { LedCommunicationState, LedCommunicationStatus, LedStateFrame } from "../types";
import { DECK_WIDGETS } from "./deckWidgets";
import styles from "./LedCommunicationWidget.module.css";

const WIDTH = 900;
const HEIGHT = 170;
const MIN_WINDOW_NS = 100_000_000;
const MAX_WINDOW_NS = 60_000_000_000;

function milliseconds(ns: number | null): string {
  return ns === null ? "—" : `${(ns / 1_000_000).toFixed(ns < 10_000_000 ? 2 : 1)} ms`;
}

export function LedCommunicationWidget({ state }: { state: LedCommunicationState }) {
  const [localStatus, setLocalStatus] = useState<LedCommunicationStatus | null>(state.status);
  const [error, setError] = useState<string | null>(null);
  const [windowNs, setWindowNs] = useState(2_000_000_000);
  const [panOffsetNs, setPanOffsetNs] = useState(0);
  const [hiddenThroughSeq, setHiddenThroughSeq] = useState(-1);
  const replayRef = useRef<HTMLInputElement>(null);

  useEffect(() => setLocalStatus(state.status), [state.status]);
  const status = localStatus ?? state.status;

  const visible = useMemo(() => {
    const edges = state.edges.filter((edge) => edge.seq > hiddenThroughSeq);
    if (edges.length === 0) return "";
    const newest = edges[edges.length - 1].monotonic_ns;
    const end = newest - panOffsetNs;
    const start = end - windowNs;
    const inWindow = edges.filter(
      (edge) => edge.monotonic_ns >= start && edge.monotonic_ns <= end,
    );
    const prior = [...edges].reverse().find((edge) => edge.monotonic_ns < start);
    const displayed = prior ? [prior, ...inWindow] : inWindow;
    if (displayed.length === 0) return "";
    let d = `M 0 ${displayed[0].level ? 30 : 140}`;
    for (const edge of displayed) {
      const x = Math.max(0, Math.min(WIDTH, ((edge.monotonic_ns - start) / windowNs) * WIDTH));
      d += ` H ${x.toFixed(2)} V ${edge.level ? 30 : 140}`;
    }
    d += ` H ${WIDTH}`;
    return d;
  }, [hiddenThroughSeq, panOffsetNs, state.edges, windowNs]);

  const historySpanNs = useMemo(() => {
    const edges = state.edges.filter((edge) => edge.seq > hiddenThroughSeq);
    return edges.length < 2
      ? 0
      : edges[edges.length - 1].monotonic_ns - edges[0].monotonic_ns;
  }, [hiddenThroughSeq, state.edges]);

  const run = async (action: () => Promise<LedCommunicationStatus>) => {
    setError(null);
    try {
      setLocalStatus(await action());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const latestMessage = state.frames.at(-1) ?? status?.latest_message ?? status?.latest_frame;
  const latestState =
    [...state.frames].reverse().find((candidate) => frameType(candidate) === "state")
    ?? status?.latest_state
    ?? status?.latest_frame;

  return (
    <section className={styles.widget} data-widget={DECK_WIDGETS.ledCommunication} data-testid="led-communication-monitor">
      <header className={styles.header}>
        <div>
          <h2>Monitor LED communication</h2>
          <p>1007.9 · 10 ms biphase-mark · STATE + LEVEL frames</p>
        </div>
        <div className={styles.liveState} data-capturing={status?.capturing ? "true" : "false"}>
          <span />{status?.capturing ? "CAPTURING" : "STOPPED"}
        </div>
      </header>

      <div className={styles.waveform} aria-label="Raw KEY_LED waveform">
        <div className={styles.axisTop}>physical 1</div>
        <div className={styles.axisBottom}>physical 0</div>
        {visible ? (
          <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" role="img">
            <path d={visible} />
          </svg>
        ) : (
          <div className={styles.empty}>Waiting for raw KEY_LED edges…</div>
        )}
        <div className={styles.timeScale}>{(windowNs / 1_000_000).toLocaleString()} ms window{panOffsetNs ? ` · ${(panOffsetNs / 1_000_000).toFixed(0)} ms behind live` : " · live edge"}</div>
      </div>

      <div className={styles.scopeControls}>
        <button
          type="button"
          disabled={Boolean(status?.capturing) || panOffsetNs + windowNs >= historySpanNs}
          onClick={() => setPanOffsetNs((value) => Math.min(Math.max(0, historySpanNs - windowNs), value + windowNs * 0.75))}
          aria-label="Scroll waveform left to older time"
        >← Older</button>
        <button
          type="button"
          disabled={Boolean(status?.capturing) || panOffsetNs === 0}
          onClick={() => setPanOffsetNs((value) => Math.max(0, value - windowNs * 0.75))}
          aria-label="Scroll waveform right to newer time"
        >Newer →</button>
        <button type="button" onClick={() => setWindowNs((value) => Math.max(MIN_WINDOW_NS, value / 2))}>Zoom in time</button>
        <button type="button" onClick={() => setWindowNs((value) => Math.min(MAX_WINDOW_NS, value * 2))}>Zoom out time</button>
        <button type="button" onClick={() => { setPanOffsetNs(0); setWindowNs(2_000_000_000); }}>Live view</button>
        <span>fixed level scale 0–1</span>
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
          <span className={styles.eyebrow}>Latest validated message</span>
          {latestMessage ? (
            <strong>{formatFrame(latestMessage)}</strong>
          ) : (
            <strong>No valid message decoded</strong>
          )}
          <span className={styles.knownState}>
            Latest STATE: {latestState ? formatState(latestState) : "not received since service start"}
          </span>
        </div>
        <code>{latestMessage?.raw_hex ?? "ffff 2dd4 1x … crc"}</code>
        <div className={styles.frameCount}>{status?.valid_frames ?? 0} valid · {status?.missing_frames ?? 0} missing</div>
      </div>

      <footer className={styles.controls}>
        <button type="button" className={styles.pauseButton} onClick={() => void run(status?.capturing ? stopLedCommunication : startLedCommunication)}>
          {status?.capturing ? "Pause capture" : "Resume capture"}
        </button>
        <button type="button" onClick={() => {
          const newestSeq = state.edges.at(-1)?.seq ?? -1;
          setHiddenThroughSeq(newestSeq);
          setPanOffsetNs(0);
          void run(clearLedCommunication);
        }}>Clear capture</button>
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

function frameType(frame: LedStateFrame): "state" | "level" | "unknown" {
  return frame.message_type ?? (frame.layout ? "state" : "unknown");
}

function formatState(frame: LedStateFrame): string {
  return `#${frame.sequence} · ${(frame.layout ?? "unknown").toUpperCase()} · ${(frame.input1 ?? "unknown").toUpperCase()} / ${(frame.input2 ?? "none").toUpperCase()}`;
}

function formatFrame(frame: LedStateFrame): string {
  const type = frameType(frame);
  const recovered = frame.acquisition_recovered ? " · recovered" : "";
  if (type === "state") return `STATE ${formatState(frame)}${recovered}`;
  if (type === "level") {
    const raw = frame.raw_value === null || frame.raw_value === undefined
      ? "—"
      : `0x${frame.raw_value.toString(16).padStart(2, "0").toUpperCase()} (${frame.raw_value})`;
    return `LEVEL #${frame.sequence} · ${levelMeaning(frame)} · raw ${raw}${recovered}`;
  }
  const typeCode = frame.type_code === undefined
    ? "??"
    : frame.type_code.toString(16).padStart(2, "0").toUpperCase();
  return `UNKNOWN #${frame.sequence} · type 0x${typeCode}${recovered}`;
}

function levelMeaning(frame: LedStateFrame): string {
  if (frame.level === 2 || frame.level === 3 || frame.level === 4) {
    return `band ${frame.level} connected`;
  }
  if (frame.level !== 0) return `band ${frame.level ?? "—"}`;
  const raw = frame.raw_value;
  if (raw === null || raw === undefined) return "none";
  if (raw >= 0x78 && raw <= 0x7f) return "released";
  if (raw <= 0x19) return "Center / band 1";
  return "none / dead zone";
}
