import { useRef, useState } from "react";

import { ConfirmDialog } from "../components/ConfirmDialog";
import { JogPad } from "../components/JogPad";
import { LedIndicator } from "../components/LedIndicator";
import { Popup } from "../components/Popup";
import { RecordingWorkspace } from "../components/RecordingWorkspace";
import { VersionBadge } from "../components/VersionBadge";
import type { DeckEventsState } from "../hooks/useDeckEvents";
import type { RecordingSummary } from "../types";
import { CalendarWidget } from "../widgets/CalendarWidget";
import { JogWidget } from "../widgets/JogWidget";
import { LiveLogWidget } from "../widgets/LiveLogWidget";
import { NotesWidget } from "../widgets/NotesWidget";
import { OsdMockPanel } from "../widgets/OsdMockPanel";

import styles from "./HomePage.module.css";

export function HomePage({ deck }: { deck: DeckEventsState }) {
  const [osdOpen, setOsdOpen] = useState(false);
  const [recordingsOpen, setRecordingsOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<RecordingSummary | null>(null);
  // The popup must not close when clicking inside the JogPad column.
  const jogColRef = useRef<HTMLDivElement>(null);

  const keyLedOn = deck.status?.signals.key_led_active ?? false;

  return (
    <div className={styles.page}>
      {deck.status && <VersionBadge version={deck.status.version} />}

      {/* Left column — JogPad + LED indicator */}
      <div className={styles.leftCol} ref={jogColRef} data-widget="jog-col">
        <div className={styles.ledCorner}>
          <LedIndicator on={keyLedOn} />
        </div>

        {/* Recording lands in Phase 16; Phase 13 places the permanent control. */}
        <button
          className={styles.recordButton}
          type="button"
          aria-label="Open recording workspace"
          title="Open recording workspace"
          onClick={() => setRecordingsOpen(true)}
        >
          <span className={styles.recordGlyph} aria-hidden="true" />
        </button>

        <JogWidget>
          <JogPad
            hardwareHeld={deck.hardwareHeld}
            wsReleaseTick={deck.wsReleaseTick}
            wsReleasedActions={deck.wsReleasedActions}
            wsSessionEpoch={deck.wsSessionEpoch}
            onLocalLog={deck.pushLogLine}
          />
        </JogWidget>

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
      </div>

      {/* Right panel — placeholder widgets */}
      <div className={styles.rightPanel}>
        <CalendarWidget />
        <NotesWidget />
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
