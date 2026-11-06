import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";

import {
  addLedCommunicationNote,
  clearLedCommunication,
  fetchLedCommunicationStatus,
  holdCommunicationHighForMeasurement,
  ledCommunicationExportUrl,
  replayLedCommunication,
  sendMonitorCommand,
  startLedCommunication,
  stopLedCommunication,
} from "../api/client";
import type {
  CommunicationHighTestResult,
  CommunicationSessionRecord,
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
const MAX_BIT_TIME_MS = 1000;
const COMMANDS = [
  [0x0, "Query", "A5 5A"], [0x1, "Single · HDMI", "A5 44"],
  [0x2, "Single · DP", "A5 77"], [0x3, "Single · TB", "A5 69"],
  [0x4, "PBP · HDMI | DP", "A5 11"], [0x5, "PBP · HDMI | TB", "A5 0F"],
  [0x6, "PBP · DP | HDMI", "A5 3C"], [0x7, "PBP · DP | TB", "A5 22"],
  [0x8, "PBP · TB | HDMI", "A5 DD"], [0x9, "PBP · TB | DP", "A5 C3"],
  [0xA, "Diagnostic", "A5 F0"],
  [0xB, "TB refresh", "A5 EE"],
  [0xE, "WATCH on / off", "A5 BB"],
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
  const [bitTimeText, setBitTimeText] = useState("25");
  const [commandCode, setCommandCode] = useState(0);
  const [commandPending, setCommandPending] = useState(false);
  const [commandResult, setCommandResult] = useState<MonitorCommandResult | null>(null);
  const [measurementPending, setMeasurementPending] = useState(false);
  const [measurementResult, setMeasurementResult] = useState<CommunicationHighTestResult | null>(null);
  const [historyOpen, setHistoryOpen] = useState<"rx" | "tx" | null>(null);
  const [sessionOpen, setSessionOpen] = useState(false);
  const [selectedSessionIds, setSelectedSessionIds] = useState<Set<string>>(new Set());
  const [copyNotice, setCopyNotice] = useState<string | null>(null);
  const replayRef = useRef<HTMLInputElement>(null);

  useEffect(() => setLocalStatus(state.status), [state.status]);
  useEffect(() => {
    if (!state.edges.length && !state.frames.length) setHiddenThroughSeq(-1);
  }, [state.edges.length, state.frames.length]);
  const status = localStatus ?? state.status;
  const rxEdges = useMemo(
    () => state.edges.filter((edge) => edge.seq > hiddenThroughSeq),
    [hiddenThroughSeq, state.edges],
  );
  const txHistory = status?.tx_history ?? [];
  const txSamples = useMemo(() => txHistory.flatMap((item) => item.samples), [txHistory]);
  const visibleFrames = useMemo(
    () => state.frames.filter((frame) => frame.edge_seq > hiddenThroughSeq),
    [hiddenThroughSeq, state.frames],
  );
  const rxHistory = visibleFrames.length ? visibleFrames : (status?.frame_history ?? []);
  const latestMessage = rxHistory.at(-1) ?? status?.latest_message ?? status?.latest_frame;
  const latestState = [...rxHistory].reverse().find((candidate) => frameType(candidate) === "state")
    ?? status?.latest_state ?? status?.latest_frame;
  const latestTx = txHistory.at(-1);
  const sessionEntries = useMemo(
    () => status?.session_history?.length
      ? buildLedgerEntries(status.session_history)
      : buildSessionEntries(rxHistory, txHistory),
    [rxHistory, status?.session_history, txHistory],
  );

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
      rx: tracePath(rxEdges, start, end, windowNs, 22, 76),
      tx: tracePath(txSamples, start, end, windowNs, 96, 150),
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
    const sendingCode = commandCode;
    const sendingBitTimeMs = normalizeBitTime(bitTimeText);
    setBitTimeText(String(sendingBitTimeMs));
    setError(null);
    setCommandPending(true);
    setPanOffsetNs(0);
    setWindowNs((current) => Math.max(
      current,
      Math.min(MAX_WINDOW_NS, (sendingBitTimeMs * 16 + 500) * 1_000_000),
    ));
    try {
      setCommandResult(await sendMonitorCommand(sendingCode, sendingBitTimeMs));
      setLocalStatus(await fetchLedCommunicationStatus());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCommandPending(false);
    }
  };

  const holdHighForMeasurement = async () => {
    setError(null);
    setMeasurementResult(null);
    setMeasurementPending(true);
    try { setMeasurementResult(await holdCommunicationHighForMeasurement()); } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setMeasurementPending(false);
    }
  };

  const clearCapture = async () => {
    setError(null);
    setHiddenThroughSeq(Math.max(
      state.edges.at(-1)?.seq ?? -1,
      ...state.frames.map((frame) => frame.edge_seq),
    ));
    try {
      setLocalStatus(await clearLedCommunication());
      setCommandResult(null);
      setMeasurementResult(null);
      setHistoryOpen(null);
      setSessionOpen(false);
      setSelectedSessionIds(new Set());
      setCopyNotice(null);
      setPanOffsetNs(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const addNote = async (text: string) => {
    setLocalStatus(await addLedCommunicationNote(text));
  };

  const maxPan = Math.max(0, timeline.span - windowNs);
  const selectedCommand = COMMANDS.find(([code]) => code === commandCode) ?? COMMANDS[0];
  const displayedCommandResult = status?.last_command ?? commandResult;

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
          <Tool label={status?.capturing ? "Pause capture" : "Resume capture"} icon={status?.capturing ? <PauseIcon /> : <PlayIcon />} onClick={() => void run(status?.capturing ? stopLedCommunication : startLedCommunication)} />
          <Tool label="Clear complete capture and session" icon={<TrashIcon />} onClick={() => void clearCapture()} />
          <button type="button" className={`${styles.toolButton} ${styles.sessionButton}`} title="Open communication session" aria-label="Open communication session" onClick={() => setSessionOpen(true)}>SESSION <b>{sessionEntries.length}</b></button>
          <a className={styles.toolButton} href={ledCommunicationExportUrl()} download="key-led-capture.json" title="Export capture" aria-label="Export capture">⇩</a>
          <Tool label="Replay capture" icon="↥" onClick={() => replayRef.current?.click()} />
          <input ref={replayRef} className={styles.hiddenInput} type="file" accept="application/json,.json" onChange={(event) => {
            const file = event.target.files?.[0]; event.target.value = "";
            if (file) void file.text().then(JSON.parse).then((document) => run(() => replayLedCommunication(document))).catch((e) => setError(String(e)));
          }} />
        </div>
        <div className={styles.scopeLegend}><span data-trace="rx" />RX KEY_LED <span data-trace="tx" />TX KEY_ADC1</div>
      </div>

      <div className={styles.waveform} aria-label="Shared monitor communication waveform">
        <div className={styles.rxAxisHigh}>RX 1</div><div className={styles.rxAxisLow}>RX 0</div>
        <div className={styles.txAxisHigh}>TX 1</div><div className={styles.txAxisLow}>TX 0</div>
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
          <small>{formatCommandResult(displayedCommandResult)} · {txHistory.length} messages</small>
        </button>
      </div>

      <div className={styles.sender}>
        <label>Message<select value={commandCode} disabled={measurementPending} onChange={(event) => setCommandCode(Number(event.target.value))}>{COMMANDS.map(([code, label, frame]) => <option key={code} value={code}>{label} · {frame}</option>)}</select></label>
        <label>Speed<input type="number" min={1} max={MAX_BIT_TIME_MS} value={bitTimeText} disabled={commandPending || measurementPending} onChange={(event) => setBitTimeText(event.target.value)} onBlur={() => setBitTimeText(String(normalizeBitTime(bitTimeText)))} /><span>ms/bit</span></label>
        <code>{selectedCommand[2]}</code>
        <button type="button" className={styles.measureButton} disabled={commandPending || measurementPending} title="Hold the custom KEY_ADC1 transmitter high for three seconds for multimeter measurement" onClick={() => void holdHighForMeasurement()}>{measurementPending ? "HIGH — MEASURE" : measurementResult ? "HIGH 3s ✓" : "HIGH 3s"}</button>
        <button type="button" disabled={commandPending || measurementPending || !status?.capturing} onClick={() => void transmit()}>{commandPending ? "SENDING…" : "SEND"}</button>
      </div>

      {error && <div className={styles.error}>{error}</div>}
      {historyOpen && <HistoryOverlay direction={historyOpen} frames={rxHistory} transmissions={txHistory} onClose={() => setHistoryOpen(null)} />}
      {sessionOpen && <SessionOverlay entries={sessionEntries} selectedIds={selectedSessionIds} copyNotice={copyNotice} onSelectionChange={setSelectedSessionIds} onCopyNotice={setCopyNotice} onAddNote={addNote} onClose={() => setSessionOpen(false)} />}
    </section>
  );
}

function tracePath(samples: readonly (LedCommunicationEdge | MonitorTxSample)[], start: number, end: number, windowNs: number, highY: number, lowY: number): string {
  const inWindow = samples.filter((sample) => sample.monotonic_ns >= start && sample.monotonic_ns <= end);
  const prior = [...samples].reverse().find((sample) => sample.monotonic_ns < start);
  const displayed = prior ? [prior, ...inWindow] : inWindow;
  if (!displayed.length) return "";
  let path = `M 0 ${displayed[0].level ? highY : lowY}`;
  for (const sample of displayed) {
    const x = Math.max(0, Math.min(WIDTH, ((sample.monotonic_ns - start) / windowNs) * WIDTH));
    path += ` H ${x.toFixed(2)} V ${sample.level ? highY : lowY}`;
  }
  return `${path} H ${WIDTH}`;
}

function Tool({ label, icon, disabled = false, active = false, onClick }: { label: string; icon: ReactNode; disabled?: boolean; active?: boolean; onClick: () => void }) {
  return <button type="button" className={styles.toolButton} title={label} aria-label={label} disabled={disabled} data-active={active ? "true" : "false"} onClick={onClick}>{icon}</button>;
}

function PauseIcon() { return <svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="2" width="3.5" height="12" rx=".7" /><rect x="9.5" y="2" width="3.5" height="12" rx=".7" /></svg>; }
function PlayIcon() { return <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5 13 8l-9 5.5z" /></svg>; }
function TrashIcon() { return <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5.5 2h5l.7 1.5H14v2H2v-2h2.8zM3.5 6.5h9l-.7 7.5H4.2z" /></svg>; }

function Metric({ label, value, warn = false }: { label: string; value: string; warn?: boolean }) {
  return <span data-warn={warn ? "true" : "false"}><b>{label}</b>{value}</span>;
}

function HistoryOverlay({ direction, frames, transmissions, onClose }: { direction: "rx" | "tx"; frames: readonly LedStateFrame[]; transmissions: readonly MonitorTransmission[]; onClose: () => void }) {
  const count = direction === "rx" ? frames.length : transmissions.length;
  return <div className={styles.historyOverlay} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section role="dialog" aria-modal="true" aria-label={`${direction === "rx" ? "Received" : "Sent"} message history`}><header><h3>{direction === "rx" ? "Received" : "Sent"} message history</h3><button type="button" aria-label="Close history" onClick={onClose}>×</button></header><div className={styles.historyList}>{direction === "rx" ? [...frames].reverse().map((frame) => <div key={`${frame.edge_seq}-${frame.sequence}`}><strong>{formatFrame(frame)}</strong><code>{frame.raw_hex}</code></div>) : [...transmissions].reverse().map((tx, index) => <div key={`${tx.monotonic_ns}-${index}`}><strong>{formatTransmission(tx)}</strong><code>{tx.frame_hex.toUpperCase()} · {tx.bit_time_ms} ms/bit · {tx.status}</code></div>)}{count === 0 && <p>No messages recorded.</p>}</div></section></div>;
}

type SessionEntry = {
  id: string;
  monotonicNs: number;
  timestamp: string | null;
  direction: "IN" | "OUT" | "NOTE";
  kind: "REQUEST" | "RESPONSE" | "UNSOLICITED" | "BAD CRC" | "INCOMPLETE" | "NOTE";
  raw: string;
  decoded: string;
};

function commandDisplayName(code: number | undefined, name: string): string {
  return code === 0xE ? "WATCH ON/OFF" : name.replaceAll("_", " ").toUpperCase();
}

function buildLedgerEntries(records: readonly CommunicationSessionRecord[]): SessionEntry[] {
  return records.map((record) => ({
    id: record.id,
    monotonicNs: record.monotonic_ns,
    timestamp: record.timestamp,
    direction: record.direction,
    kind: record.kind,
    raw: record.raw_hex?.toUpperCase() ?? "",
    decoded: record.note ?? record.reason ?? (record.frame
      ? formatFrame(record.frame)
      : `${commandDisplayName(record.command_code, record.command_name ?? "reserved")} · ${record.bit_time_ms ?? "—"} ms/bit`),
  }));
}

function frameKey(frame: LedStateFrame): string { return `${frame.edge_seq}:${frame.raw_hex}`; }
function buildSessionEntries(frames: readonly LedStateFrame[], transmissions: readonly MonitorTransmission[]): SessionEntry[] {
  const responseFrames = new Set<string>();
  for (const tx of transmissions) {
    for (const frame of [tx.state, tx.diagnostic, tx.presence, tx.scan, tx.refresh]) {
      if (frame) responseFrames.add(frameKey(frame));
    }
  }
  return [
    ...transmissions.map((tx): SessionEntry => ({
      id: `tx-${tx.monotonic_ns}`,
      monotonicNs: tx.monotonic_ns,
      timestamp: tx.sent_at ?? null,
      direction: "OUT",
      kind: "REQUEST",
      raw: tx.frame_hex.toUpperCase(),
      decoded: `${commandDisplayName(tx.command_code, tx.command_name)} · ${tx.bit_time_ms} ms/bit`,
    })),
    ...frames.map((frame): SessionEntry => ({
      id: `rx-${frame.edge_seq}-${frame.raw_hex}`,
      monotonicNs: frame.monotonic_ns,
      timestamp: frame.received_at ?? null,
      direction: "IN",
      kind: responseFrames.has(frameKey(frame)) ? "RESPONSE" : "UNSOLICITED",
      raw: frame.raw_hex.toUpperCase(),
      decoded: formatFrame(frame),
    })),
  ].sort((a, b) => a.monotonicNs - b.monotonicNs);
}

function sessionLine(entry: SessionEntry, firstNs: number): string {
  const timestamp = entry.timestamp ?? `+${((entry.monotonicNs - firstNs) / 1_000_000_000).toFixed(3)}s`;
  if (entry.kind === "NOTE") return `${timestamp}  NOTE              ${entry.decoded}`;
  return `${timestamp}  ${entry.direction.padEnd(3)}  ${entry.kind.padEnd(11)}  RAW ${entry.raw}  ${entry.decoded}`;
}

async function copyText(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Plain-HTTP kiosk sessions commonly reject the modern clipboard API. Fall through to
      // the synchronous user-gesture path supported by Chromium.
    }
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  textarea.setSelectionRange(0, textarea.value.length);
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } finally {
    textarea.remove();
  }
  return copied;
}

function SessionOverlay({ entries, selectedIds, copyNotice, onSelectionChange, onCopyNotice, onAddNote, onClose }: { entries: readonly SessionEntry[]; selectedIds: Set<string>; copyNotice: string | null; onSelectionChange: (ids: Set<string>) => void; onCopyNotice: (notice: string | null) => void; onAddNote: (text: string) => Promise<void>; onClose: () => void }) {
  const [noteText, setNoteText] = useState("");
  const [notePending, setNotePending] = useState(false);
  const firstNs = entries[0]?.monotonicNs ?? 0;
  const copy = async (selectedOnly: boolean) => {
    const chosen = selectedOnly ? entries.filter((entry) => selectedIds.has(entry.id)) : entries;
    if (!chosen.length) return;
    const copied = await copyText(chosen.map((entry) => sessionLine(entry, firstNs)).join("\n"));
    if (copied) {
      onCopyNotice(`Copied ${chosen.length} message${chosen.length === 1 ? "" : "s"}`);
    } else {
      onCopyNotice("Copy was blocked by the browser");
    }
  };
  const toggle = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    onSelectionChange(next);
    onCopyNotice(null);
  };
  const submitNote = async () => {
    const note = noteText.trim();
    if (!note) return;
    setNotePending(true);
    try { await onAddNote(note); setNoteText(""); } finally { setNotePending(false); }
  };
  return <div className={styles.historyOverlay} role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className={styles.sessionDialog} role="dialog" aria-modal="true" aria-label="Communication session"><header><h3>Communication session · {entries.length} messages</h3><button type="button" aria-label="Close session" onClick={onClose}>×</button></header><form className={styles.noteBar} onSubmit={(event) => { event.preventDefault(); void submitNote(); }}><input aria-label="Session note" value={noteText} maxLength={1000} placeholder="Add a timestamped test note…" onChange={(event) => setNoteText(event.target.value)} /><button type="submit" disabled={notePending || !noteText.trim()}>{notePending ? "ADDING…" : "ADD NOTE"}</button></form><div className={styles.sessionActions}><button type="button" onClick={() => onSelectionChange(new Set(entries.map((entry) => entry.id)))}>Select all</button><button type="button" onClick={() => onSelectionChange(new Set())}>Select none</button><button type="button" disabled={!selectedIds.size} onClick={() => void copy(true)}>Copy selected ({selectedIds.size})</button><button type="button" disabled={!entries.length} onClick={() => void copy(false)}>Copy all</button>{copyNotice && <span role="status">{copyNotice}</span>}</div><div className={`${styles.historyList} ${styles.sessionList}`}>{entries.map((entry) => <label key={entry.id}><input type="checkbox" checked={selectedIds.has(entry.id)} onChange={() => toggle(entry.id)} /><time>{entry.timestamp ?? `+${((entry.monotonicNs - firstNs) / 1_000_000_000).toFixed(3)}s`}</time><b data-direction={entry.direction}>{entry.direction}</b><em>{entry.kind}</em><code>{entry.raw}</code><span>{entry.decoded}</span></label>)}{entries.length === 0 && <p>No communication messages recorded.</p>}</div></section></div>;
}

function frameType(frame: LedStateFrame): NonNullable<LedStateFrame["message_type"]> { return frame.message_type ?? (frame.layout ? "state" : "unknown"); }
function formatState(frame: LedStateFrame): string {
  const mask = frame.connection_mask;
  const connected = mask == null ? "" : ` · CONN ${mask & 1 ? "H" : "-"}${mask & 2 ? "D" : "-"}${mask & 4 ? "T" : "-"}`;
  return `#${frame.sequence} · ${(frame.layout ?? "unknown").toUpperCase()} · ${(frame.input1 ?? "unknown").toUpperCase()} / ${(frame.input2 ?? "none").toUpperCase()}${connected}`;
}
function hex(value: number | null | undefined): string { return value == null ? "—" : `0x${value.toString(16).padStart(2, "0").toUpperCase()}`; }
function normalizeBitTime(value: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return 25;
  return Math.max(1, Math.min(MAX_BIT_TIME_MS, Math.trunc(parsed)));
}
function presenceSources(mask: number | null | undefined): string {
  if (mask == null) return "unknown inputs";
  const sources = [
    mask & 0x01 ? "HDMI" : null,
    mask & 0x02 ? "TB" : null,
    mask & 0x04 ? "DP" : null,
  ].filter((source): source is string => source !== null);
  return sources.length ? sources.join(" + ") : "none reported";
}
function windowState(value: number | null | undefined): string {
  if (value == null) return "unknown";
  if (value === 0x0) return "off";
  if (value === 0x5) return "searching";
  if (value >= 0x6 && value <= 0xA) return `locking (${value.toString(16).toUpperCase()})`;
  if (value === 0xB) return "picture";
  return `state ${value.toString(16).toUpperCase()}`;
}
const WATCH_NAMES = [
  "HDMI detection record", "TB detection record", "DP detection record",
  "TB presence ADC", "DP presence ADC", "TB receiver status bit",
  "DP receiver status bit", "TB receiver control bit", "HDMI clock detect",
  "receiver clock states", "HDMI new-signal latch", "TB new-signal latch",
  "DP new-signal latch", "window 0 state", "window 1 state", "presence mask",
];
function watchValueMeaning(index: number | null | undefined, value: number | null | undefined): string {
  if (index == null || value == null) return "";
  if (index <= 2) {
    const states: Record<number, string> = { 1: "off", 2: "reset", 3: "locked / no stream", 4: "measuring", 5: "stable signal", 6: "power save", 7: "power save" };
    return states[value & 0x0F] ? ` (${states[value & 0x0F]})` : "";
  }
  if (index === 13 || index === 14) return ` (${windowState(value & 0x0F)})`;
  return "";
}
function refreshResult(value: number | null | undefined): string {
  const meanings: Record<number, string> = {
    0x00: "done: TB dropped and raised",
    0x01: "done: TB was already raised",
    0x02: "done: monitor will raise TB",
    0x10: "skipped: TB hot-plug already low",
    0x11: "skipped: port held low",
    0x12: "skipped: power-save state",
    0x13: "skipped: refresh already running",
  };
  return value == null ? "unknown result" : (meanings[value] ?? `result ${hex(value)}`);
}
function formatFrame(frame: LedStateFrame): string {
  switch (frameType(frame)) {
    case "state": return `STATE ${formatState(frame)}`;
    case "level": return `LEVEL #${frame.sequence} · ${frame.level && frame.level >= 2 && frame.level <= 4 ? `band ${frame.level} connected` : `band ${frame.level ?? "—"}`} · raw ${hex(frame.raw_value)}${frame.raw_value == null ? "" : ` (${frame.raw_value})`}`;
    case "hold": return `HOLD #${frame.sequence} · raw ${hex(frame.min_raw)}–${hex(frame.max_raw)}`;
    case "rate": return `RATE #${frame.sequence} · gap ${frame.shortest_gap_ticks ?? "—"}–${frame.longest_gap_ticks ?? "—"} ticks`;
    case "diag": return `DIAG #${frame.sequence} · ${frame.diagnostic_reads ?? "—"} ADC reads · ${frame.diagnostic_conversions_stopped ? "conversions stopped" : "conversions running"} · ${frame.diagnostic_timeouts ?? "—"} timeouts · ${frame.diagnostic_rejected_frames ?? "—"} rejected frames`;
    case "presence": return `PRESENCE #${frame.sequence} · ${presenceSources(frame.presence_mask)} reported · left ${windowState(frame.presence_window0_state)} · right ${windowState(frame.presence_window1_state)} · raw mask ${hex(frame.presence_mask)}`;
    case "scan": return `SCAN #${frame.sequence} · longest scan gap ${frame.scan_longest_gap_ms === 0xFF ? "≥255" : frame.scan_longest_gap_ms ?? "—"} ms · last scan ${frame.scan_last_ms ?? "—"} ms ago`;
    case "refresh": return `REFRESH #${frame.sequence} · ${refreshResult(frame.refresh_result)} · hot-plug flags ${hex(frame.refresh_flags)}`;
    case "watch": return `WATCH #${frame.sequence} · [${frame.watch_index ?? "—"}] ${WATCH_NAMES[frame.watch_index ?? -1] ?? "unknown watch value"} = ${(frame.watch_value ?? 0).toString(16).padStart(2, "0").toUpperCase()}${watchValueMeaning(frame.watch_index, frame.watch_value)}`;
    case "bad_crc": return `BAD CRC #${frame.sequence} · received ${hex(frame.crc)} · expected ${hex(frame.expected_crc)}`;
    case "ack": return `ACK #${frame.sequence} · ${ackMeaning(frame.ack_result)} · code ${frame.ack_code?.toString(16).toUpperCase() ?? "—"} · T ${frame.measured_bit_ticks ?? "—"}`;
    default: return `UNKNOWN #${frame.sequence} · type ${hex(frame.type_code)}${recovered}`;
  }
}
function ackMeaning(code: number | null | undefined): string { return code == null ? "unknown result" : (ACK_RESULTS[code] ?? `result ${code}`); }
function formatTransmission(tx: MonitorTransmission): string { return `${commandDisplayName(tx.command_code, tx.command_name)} · ${tx.bit_time_ms} ms/bit · ${tx.status}`; }
function formatCommandResult(result: MonitorCommandResult | null): string {
  if (!result) return "Ready";
  if (result.status === "response") return result.command_code === 0xA
    ? `Diagnostic response · DIAG #${result.diagnostic?.sequence ?? "—"} + PRESENCE #${result.presence?.sequence ?? "—"} + SCAN #${result.scan?.sequence ?? "—"}`
    : result.command_code === 0xB
      ? `TB refresh response · ${refreshResult(result.refresh?.refresh_result)}`
      : `${result.command_code === 0 ? "Query" : "Command"} response · STATE #${result.state?.sequence ?? "—"}`;
  if (result.status === "partial_response") return "Partial response";
  if (result.status === "timeout") return "No response in 5 s";
  if (result.status === "superseded") return "Response wait superseded by newer command";
  return "Waiting for response";
}
