import { useEffect, useMemo, useRef, useState } from "react";

import {
  clearLedCommunication,
  ledCommunicationExportUrl,
  replayLedCommunication,
  sendMonitorCommand,
  startLedCommunication,
  stopLedCommunication,
} from "../api/client";
import type {
  LedCommunicationEdge,
  LedCommunicationState,
  LedCommunicationStatus,
  LedStateFrame,
  MonitorCommandResult,
  MonitorTransmission,
  MonitorTxSample,
} from "../types";
import { DECK_WIDGETS } from "./deckWidgets";
import styles from "./LedCommunicationWidget.module.css";

const WIDTH = 900;
const HEIGHT = 170;
const MIN_WINDOW_NS = 20_000_000;
const MAX_WINDOW_NS = 60_000_000_000;
const COMMANDS = [
  [0x0, "Query", "A5 5A"], [0x1, "Single · HDMI", "A5 44"],
  [0x2, "Single · DP", "A5 77"], [0x3, "Single · TB", "A5 69"],
  [0x4, "PBP · HDMI | DP", "A5 11"], [0x5, "PBP · HDMI | TB", "A5 0F"],
  [0x6, "PBP · DP | HDMI", "A5 3C"], [0x7, "PBP · DP | TB", "A5 22"],
  [0x8, "PBP · TB | HDMI", "A5 DD"], [0x9, "PBP · TB | DP", "A5 C3"],
] as const;
const ACK_RESULTS: Record<number, string> = {
  0: "valid, not executed", 1: "executed", 2: "unknown / reserved",
  3: "already in state", 4: "refused: menu open", 8: "check bits wrong",
  9: "timing / level error",
};

function milliseconds(ns: number | null): string {
  return ns === null ? "—" : `${(ns / 1_000_000).toFixed(ns < 10_000_000 ? 2 : 1)} ms`;
}

export function LedCommunicationWidget({ state }: { state: LedCommunicationState }) {
  const [localStatus, setLocalStatus] = useState<LedCommunicationStatus | null>(state.status);
  const [error, setError] = useState<string | null>(null);
  const [windowNs, setWindowNs] = useState(2_000_000_000);
  const [panOffsetNs, setPanOffsetNs] = useState(0);
  const [hiddenThroughSeq, setHiddenThroughSeq] = useState(-1);
  const [bitTimeMs, setBitTimeMs] = useState(50);
  const [commandCode, setCommandCode] = useState(0);
  const [commandPending, setCommandPending] = useState(false);
  const [commandResult, setCommandResult] = useState<MonitorCommandResult | null>(null);
  const [historyOpen, setHistoryOpen] = useState<"rx" | "tx" | null>(null);
  const replayRef = useRef<HTMLInputElement>(null);

  useEffect(() => setLocalStatus(state.status), [state.status]);
  const status = localStatus ?? state.status;
  const rxEdges = useMemo(
    () => state.edges.filter((edge) => edge.seq > hiddenThroughSeq),
    [hiddenThroughSeq, state.edges],
  );
  const txHistory = status?.tx_history ?? [];
  const txSamples = useMemo(() => txHistory.flatMap((item) => item.samples), [txHistory]);
  const rxHistory = state.frames.length ? state.frames : (status?.frame_history ?? []);
  const latestMessage = rxHistory.at(-1) ?? status?.latest_message ?? status?.latest_frame;
  const latestState = [...rxHistory].reverse().find((candidate) => frameType(candidate) === "state")
    ?? status?.latest_state ?? status?.latest_frame;
  const latestTx = txHistory.at(-1);

  const timeline = useMemo(() => {
    const times = [
      ...rxEdges.map((edge) => edge.monotonic_ns),
      ...txSamples.map((sample) => sample.monotonic_ns),
    ];
    if (!times.length) return { rx: "", tx: "", span: 0 };
    const newest = Math.max(...times);
    const oldest = Math.min(...times);
    const end = newest - panOffsetNs;
    const start = end - windowNs;
    return {
      rx: tracePath(rxEdges, start, end, windowNs),
      tx: tracePath(txSamples, start, end, windowNs),
      span: newest - oldest,
    };
  }, [panOffsetNs, rxEdges, txSamples, windowNs]);

  const run = async (action: () => Promise<LedCommunicationStatus>) => {
    setError(null);
    try { setLocalStatus(await action()); } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const transmit = async () => {
    setError(null);
    setCommandPending(true);
    try { setCommandResult(await sendMonitorCommand(commandCode, bitTimeMs)); } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCommandPending(false);
    }
  };

  const maxPan = Math.max(0, timeline.span - windowNs);
  const selectedCommand = COMMANDS.find(([code]) => code === commandCode) ?? COMMANDS[0];

  return (
    <section className={styles.widget} data-widget={DECK_WIDGETS.ledCommunication} data-testid="led-communication-monitor">
      <header className={styles.header}>
        <h2>Monitor communication</h2>
        <div className={styles.liveState} data-capturing={status?.capturing ? "true" : "false"}>
          <span />{status?.capturing ? "CAPTURING" : "PAUSED"}
        </div>
      </header>

      <div className={styles.toolbar}>
        <div className={styles.toolGroup}>
          <Tool label="Older" icon="←" disabled={panOffsetNs >= maxPan} onClick={() => setPanOffsetNs((value) => Math.min(maxPan, value + windowNs * 0.75))} />
          <Tool label="Newer" icon="→" disabled={panOffsetNs === 0} onClick={() => setPanOffsetNs((value) => Math.max(0, value - windowNs * 0.75))} />
          <Tool label="Zoom in time" icon="＋" disabled={windowNs <= MIN_WINDOW_NS} onClick={() => setWindowNs((value) => Math.max(MIN_WINDOW_NS, value / 2))} />
          <Tool label="Zoom out time" icon="−" disabled={windowNs >= MAX_WINDOW_NS} onClick={() => setWindowNs((value) => Math.min(MAX_WINDOW_NS, value * 2))} />
        </div>
        <div className={styles.toolGroup}>
          <Tool label="Live view" icon="●" active={panOffsetNs === 0} onClick={() => setPanOffsetNs(0)} />
          <Tool label={status?.capturing ? "Pause capture" : "Resume capture"} icon={status?.capturing ? "Ⅱ" : "▶"} onClick={() => void run(status?.capturing ? stopLedCommunication : startLedCommunication)} />
          <Tool label="Clear capture" icon="⌫" onClick={() => {
            setHiddenThroughSeq(state.edges.at(-1)?.seq ?? -1);
            setPanOffsetNs(0);
            void run(clearLedCommunication);
          }} />
          <a className={styles.toolButton} href={ledCommunicationExportUrl()} download="key-led-capture.json" title="Export capture" aria-label="Export capture">⇩</a>
          <Tool label="Replay capture" icon="↥" onClick={() => replayRef.current?.click()} />
          <input ref={replayRef} className={styles.hiddenInput} type="file" accept="application/json,.json" onChange={(event) => {
            const file = event.target.files?.[0]; event.target.value = "";
            if (file) void file.text().then(JSON.parse).then((document) => run(() => replayLedCommunication(document))).catch((e) => setError(String(e)));
          }} />
        </div>
        <div className={styles.scopeLegend}><span data-trace="rx" />RX LED <span data-trace="tx" />TX Center</div>
      </div>

      <div className={styles.waveform} aria-label="Shared monitor communication waveform">
        <div className={styles.axisTop}>1</div><div className={styles.axisBottom}>0</div>
        {timeline.rx || timeline.tx ? (
          <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" role="img">
            {timeline.rx && <path className={styles.rxTrace} d={timeline.rx} />}
            {timeline.tx && <path className={styles.txTrace} d={timeline.tx} />}
          </svg>
        ) : <div className={styles.empty}>Waiting for monitor communication…</div>}
        <div className={styles.timeScale}>{(windowNs / 1_000_000).toLocaleString()} ms{panOffsetNs ? ` · ${(panOffsetNs / 1_000_000).toFixed(0)} ms behind` : " · live"}</div>
      </div>

      <div className={styles.metricStrip}>
        <Metric label="Level" value={status?.level == null ? "—" : String(status.level)} />
        <Metric label="Edges" value={String(status?.accepted_edges ?? 0)} />
        <Metric label="Median" value={milliseconds(status?.intervals.median_ns ?? null)} />
        <Metric label="Range" value={`${milliseconds(status?.intervals.min_ns ?? null)}–${milliseconds(status?.intervals.max_ns ?? null)}`} />
        <Metric label="Glitches" value={String(status?.rejected_glitches ?? 0)} warn={Boolean(status?.rejected_glitches)} />
        <Metric label="Overruns" value={String(status?.overruns ?? 0)} warn={Boolean(status?.overruns)} />
      </div>

      <div className={styles.messageRow}>
        <button type="button" className={styles.messageSummary} onClick={() => setHistoryOpen("rx")}>
          <span><i data-trace="rx" />Latest received</span>
          <strong>{latestMessage ? formatFrame(latestMessage) : "No validated message"}</strong>
          <small>{latestState ? `Latest STATE: ${formatState(latestState)}` : "No STATE received"} · {rxHistory.length} messages</small>
        </button>
        <button type="button" className={styles.messageSummary} onClick={() => setHistoryOpen("tx")}>
          <span><i data-trace="tx" />Latest sent</span>
          <strong>{latestTx ? formatTransmission(latestTx) : "No message sent"}</strong>
          <small>{formatCommandResult(commandResult ?? status?.last_command ?? null)} · {txHistory.length} messages</small>
        </button>
      </div>

      <div className={styles.sender}>
        <label>Message<select value={commandCode} disabled={commandPending} onChange={(event) => setCommandCode(Number(event.target.value))}>{COMMANDS.map(([code, label, frame]) => <option key={code} value={code}>{label} · {frame}</option>)}</select></label>
        <label>Speed<input type="number" min={1} max={50} value={bitTimeMs} disabled={commandPending} onChange={(event) => setBitTimeMs(Math.max(1, Math.min(50, Number(event.target.value) || 1)))} /><span>ms/bit</span></label>
        <code>{selectedCommand[2]}</code>
        <button type="button" disabled={commandPending || !status?.capturing} onClick={() => void transmit()}>{commandPending ? "WAITING FOR ACK…" : "SEND"}</button>
      </div>

      {error && <div className={styles.error}>{error}</div>}
      {historyOpen && <HistoryOverlay direction={historyOpen} frames={rxHistory} transmissions={txHistory} onClose={() => setHistoryOpen(null)} />}
    </section>
  );
}

function tracePath(samples: readonly (LedCommunicationEdge | MonitorTxSample)[], start: number, end: number, windowNs: number): string {
  const inWindow = samples.filter((sample) => sample.monotonic_ns >= start && sample.monotonic_ns <= end);
  const prior = [...samples].reverse().find((sample) => sample.monotonic_ns < start);
  const displayed = prior ? [prior, ...inWindow] : inWindow;
  if (!displayed.length) return "";
  let path = `M 0 ${displayed[0].level ? 30 : 140}`;
  for (const sample of displayed) {
    const x = Math.max(0, Math.min(WIDTH, ((sample.monotonic_ns - start) / windowNs) * WIDTH));
    path += ` H ${x.toFixed(2)} V ${sample.level ? 30 : 140}`;
  }
  return `${path} H ${WIDTH}`;
}

function Tool({ label, icon, disabled = false, active = false, onClick }: { label: string; icon: string; disabled?: boolean; active?: boolean; onClick: () => void }) {
  return <button type="button" className={styles.toolButton} title={label} aria-label={label} disabled={disabled} data-active={active ? "true" : "false"} onClick={onClick}>{icon}</button>;
}

function Metric({ label, value, warn = false }: { label: string; value: string; warn?: boolean }) {
  return <span data-warn={warn ? "true" : "false"}><b>{label}</b>{value}</span>;
}

function HistoryOverlay({ direction, frames, transmissions, onClose }: { direction: "rx" | "tx"; frames: readonly LedStateFrame[]; transmissions: readonly MonitorTransmission[]; onClose: () => void }) {
  const count = direction === "rx" ? frames.length : transmissions.length;
  return <div className={styles.historyOverlay} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section role="dialog" aria-modal="true" aria-label={`${direction === "rx" ? "Received" : "Sent"} message history`}><header><h3>{direction === "rx" ? "Received" : "Sent"} message history</h3><button type="button" aria-label="Close history" onClick={onClose}>×</button></header><div className={styles.historyList}>{direction === "rx" ? [...frames].reverse().map((frame) => <div key={`${frame.edge_seq}-${frame.sequence}`}><strong>{formatFrame(frame)}</strong><code>{frame.raw_hex}</code></div>) : [...transmissions].reverse().map((tx, index) => <div key={`${tx.monotonic_ns}-${index}`}><strong>{formatTransmission(tx)}</strong><code>{tx.frame_hex.toUpperCase()} · {tx.bit_time_ms} ms/bit · {tx.status}</code></div>)}{count === 0 && <p>No messages recorded.</p>}</div></section></div>;
}

function frameType(frame: LedStateFrame): NonNullable<LedStateFrame["message_type"]> { return frame.message_type ?? (frame.layout ? "state" : "unknown"); }
function formatState(frame: LedStateFrame): string { return `#${frame.sequence} · ${(frame.layout ?? "unknown").toUpperCase()} · ${(frame.input1 ?? "unknown").toUpperCase()} / ${(frame.input2 ?? "none").toUpperCase()}`; }
function hex(value: number | null | undefined): string { return value == null ? "—" : `0x${value.toString(16).padStart(2, "0").toUpperCase()}`; }
function formatFrame(frame: LedStateFrame): string {
  const recovered = frame.acquisition_recovered ? " · recovered" : "";
  switch (frameType(frame)) {
    case "state": return `STATE ${formatState(frame)}${recovered}`;
    case "level": return `LEVEL #${frame.sequence} · ${frame.level && frame.level >= 2 && frame.level <= 4 ? `band ${frame.level} connected` : `band ${frame.level ?? "—"}`} · raw ${hex(frame.raw_value)}${frame.raw_value == null ? "" : ` (${frame.raw_value})`}${recovered}`;
    case "hold": return `HOLD #${frame.sequence} · raw ${hex(frame.min_raw)}–${hex(frame.max_raw)}${recovered}`;
    case "rate": return `RATE #${frame.sequence} · gap ${frame.shortest_gap_ticks ?? "—"}–${frame.longest_gap_ticks ?? "—"} ticks${recovered}`;
    case "ack": return `ACK #${frame.sequence} · ${ackMeaning(frame.ack_result)} · code ${frame.ack_code?.toString(16).toUpperCase() ?? "—"} · T ${frame.measured_bit_ticks ?? "—"}${recovered}`;
    default: return `UNKNOWN #${frame.sequence} · type ${hex(frame.type_code)}${recovered}`;
  }
}
function ackMeaning(code: number | null | undefined): string { return code == null ? "unknown result" : (ACK_RESULTS[code] ?? `result ${code}`); }
function formatTransmission(tx: MonitorTransmission): string { return `${tx.command_name.replaceAll("_", " ").toUpperCase()} · ${tx.bit_time_ms} ms/bit · ${tx.status}`; }
function formatCommandResult(result: MonitorCommandResult | null): string {
  if (!result) return "Ready";
  if (result.status === "timeout") return "No ACK in 3 s";
  if (result.status === "ack") return `${ackMeaning(result.ack?.ack_result)} · measured ${result.ack?.measured_bit_ticks ?? "—"} ticks`;
  return "Waiting for ACK";
}
