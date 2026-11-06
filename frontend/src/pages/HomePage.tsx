import { useRef, useState } from "react";

import { ConfirmDialog } from "../components/ConfirmDialog";
import { JogPad } from "../components/JogPad";
import { LedIndicator } from "../components/LedIndicator";
import { Popup } from "../components/Popup";
import { RecordingWorkspace } from "../components/RecordingWorkspace";
import { sendMonitorCommand } from "../api/client";
import type { DeckEventsState } from "../hooks/useDeckEvents";
import type { RecordingSummary } from "../types";
import { JogWidget } from "../widgets/JogWidget";
import { LedCommunicationWidget } from "../widgets/LedCommunicationWidget";
import { LiveLogWidget } from "../widgets/LiveLogWidget";
import { OsdMockPanel } from "../widgets/OsdMockPanel";

import styles from "./HomePage.module.css";

type QuickSource = "TB" | "HDMI" | "DP";

const SOURCE_MASK: Record<QuickSource, number> = { HDMI: 0x1, DP: 0x2, TB: 0x4 };

const QUICK_SOURCE_COMMANDS: readonly {
  code: number;
  label: string;
  sources: readonly [QuickSource] | readonly [QuickSource, QuickSource];
}[] = [
  { code: 0x9, label: "TB | DP", sources: ["TB", "DP"] },
  { code: 0x8, label: "TB | HDMI", sources: ["TB", "HDMI"] },
  { code: 0x4, label: "HDMI | DP", sources: ["HDMI", "DP"] },
  { code: 0x3, label: "TB", sources: ["TB"] },
  { code: 0x1, label: "HDMI", sources: ["HDMI"] },
  { code: 0x2, label: "DP", sources: ["DP"] },
];

function SourceLayoutIcon({ sources }: { sources: readonly QuickSource[] }) {
  return (
    <span className={styles.monitorIcon} aria-hidden="true">
      <span className={styles.monitorScreen} data-split={sources.length === 2 ? "true" : "false"}>
        {sources.map((source) => <span key={source} data-source={source}>{source}</span>)}
      </span>
      <span className={styles.monitorStand} />
    </span>
  );
}

export function HomePage({ deck }: { deck: DeckEventsState }) {
  const [osdOpen, setOsdOpen] = useState(false);
  const [recordingsOpen, setRecordingsOpen] = useState(false);
  const [monitorCommandPending, setMonitorCommandPending] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<RecordingSummary | null>(null);
  // The popup must not close when clicking inside the JogPad column.
  const jogColRef = useRef<HTMLDivElement>(null);

  // The monitor is configured with its power LED off while awake.  Keep the deck's
  // interpreted indicator intentionally inverse so an awake/LED-off monitor reads ON here.
  const keyLedOn = !(deck.status?.signals.key_led_active ?? false);
  const communicationStatus = deck.ledCommunication.status;
  const monitorState = communicationStatus?.latest_state ?? communicationStatus?.latest_frame;
  const stateIsValid = communicationStatus?.state_valid !== false
    && monitorState?.message_type !== "bad_crc"
    && ["single", "pbp", "pip"].includes(monitorState?.layout ?? "")
    && ["hdmi", "dp", "tb"].includes(monitorState?.input1 ?? "")
    && typeof monitorState?.connection_mask === "number";

  function quickControlIsSelected(sources: readonly QuickSource[]) {
    if (!stateIsValid || !monitorState) return false;
    const normalized = sources.map((source) => source.toLowerCase());
    if (sources.length === 1) {
      return monitorState.layout === "single" && monitorState.input1 === normalized[0];
    }
    return monitorState.layout === "pbp"
      && monitorState.input1 === normalized[0]
      && monitorState.input2 === normalized[1];
  }

  function quickControlHasDisconnectedSource(sources: readonly QuickSource[]) {
    if (!stateIsValid || typeof monitorState?.connection_mask !== "number") return false;
    return sources.some((source) => (monitorState.connection_mask! & SOURCE_MASK[source]) === 0);
  }

  async function sendQuickMonitorCommand(code: number, label: string) {
    setMonitorCommandPending(code);
    try {
      await sendMonitorCommand(code, 25);
      deck.pushLogLine(`${label} sent — waiting for monitor response`);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      deck.pushLogLine(`${label} failed — ${message}`);
    } finally {
      setMonitorCommandPending(null);
    }
  }

  return (
    <div className={styles.page}>
      {/* Left column — status controls above a bottom-aligned JogPad */}
      <div className={styles.leftCol} ref={jogColRef} data-widget="jog-col">
        <div className={styles.topControls}>
          <div className={styles.ledControl}>
            <LedIndicator on={keyLedOn} />
          </div>

          <button
            className={styles.tbRefreshButton}
            type="button"
            disabled={monitorCommandPending !== null}
            onClick={() => void sendQuickMonitorCommand(0xB, "TB refresh")}
            aria-label="Refresh Thunderbolt connection"
            aria-busy={monitorCommandPending === 0xB}
            title="TB refresh · command B · A5 EE"
            data-pending={monitorCommandPending === 0xB ? "true" : "false"}
          >
            <span aria-hidden="true">↻</span>
          </button>

          <button
            className={styles.osdTrigger}
            type="button"
            onClick={() => setOsdOpen(true)}
            aria-label="Show OSD mock"
            data-testid="osd-trigger"
            title="Open OSD mock panel"
          >
            OSD
          </button>

          <button
            className={styles.recordButton}
            type="button"
            aria-label="Open recording workspace"
            title="Open recording workspace"
            onClick={() => setRecordingsOpen(true)}
          >
            <svg width="48" height="48" viewBox="0 0 48 48" aria-hidden="true"
              style={{ filter: "drop-shadow(0 4px 10px rgba(0,0,0,0.4))" }}
            >
              {/* Outer ring — stroke only, no fill gradient */}
              <circle cx="24" cy="24" r="22"
                fill="rgba(18,24,32,0.72)"
                stroke="rgba(255,100,90,0.65)"
                strokeWidth="1.25"
              />
              {/* Inner red dot — flat fill */}
              <circle cx="24" cy="24" r="9"
                fill="#e05a52"
                style={{ filter: "drop-shadow(0 0 5px rgba(255,80,70,0.8))" }}
              />
              {/* Specular */}
              <ellipse cx="20.5" cy="19.5" rx="3.5" ry="2.2" fill="rgba(255,255,255,0.25)" />
            </svg>
          </button>
        </div>

        <div
          className={styles.quickControls}
          role="group"
          aria-label="Quick source and layout controls"
          aria-busy={communicationStatus?.state_recovery_pending === true}
          data-state={stateIsValid ? "valid" : "uncertain"}
        >
          {QUICK_SOURCE_COMMANDS.map(({ code, label, sources }) => {
            const selected = quickControlIsSelected(sources);
            const disconnected = quickControlHasDisconnectedSource(sources);
            return (
              <button
                key={code}
                className={styles.quickControlButton}
                type="button"
                disabled={monitorCommandPending !== null}
                aria-label={label}
                aria-pressed={selected}
                title={`${label} · command ${code.toString(16).toUpperCase()}${disconnected ? " · source disconnected" : ""}`}
                data-pending={monitorCommandPending === code ? "true" : "false"}
                data-selected={selected ? "true" : "false"}
                data-disconnected={disconnected ? "true" : "false"}
                onClick={() => void sendQuickMonitorCommand(code, label)}
              >
                <SourceLayoutIcon sources={sources} />
              </button>
            );
          })}
        </div>

        <JogWidget>
          <JogPad
            hardwareHeld={deck.hardwareHeld}
            wsReleaseTick={deck.wsReleaseTick}
            wsReleasedActions={deck.wsReleasedActions}
            wsSessionEpoch={deck.wsSessionEpoch}
            onLocalLog={deck.pushLogLine}
          />
        </JogWidget>
      </div>

      {/* Right panel — raw monitor LED communication */}
      <div className={styles.rightPanel}>
        <LedCommunicationWidget state={deck.ledCommunication} />
      </div>

      {/* Log band — fixed height, scrolls inside */}
      <div className={styles.logRow}>
        <LiveLogWidget lines={deck.logLines} onClearServerLog={deck.clearServerLog} />
      </div>

      {/* OSD popup — positioned right of JogPad, does not close on JogPad clicks */}
      <Popup
        open={osdOpen}
        onClose={() => setOsdOpen(false)}
        position="right"
        ignoreRef={jogColRef}
        title="OSD"
      >
        <OsdMockPanel />
      </Popup>

      <Popup
        open={recordingsOpen}
        onClose={() => setRecordingsOpen(false)}
        position="right"
        ignoreRef={jogColRef}
        title="Recordings (create and manage command macros)"
        size="workspace"
      >
        <RecordingWorkspace deck={deck} onRequestDelete={setPendingDelete} />
      </Popup>

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete Recording"
        message={
          pendingDelete
            ? `Delete "${pendingDelete.name}"? This removes the saved macro from the Pi.`
            : ""
        }
        confirmLabel="Delete"
        cancelLabel="Keep"
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          const item = pendingDelete;
          if (!item) {
            return;
          }
          setPendingDelete(null);
          void deck.deleteRecording(item.id);
        }}
      />
    </div>
  );
}
