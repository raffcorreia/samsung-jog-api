import { useRef, useState } from "react";

import { JogPad } from "../components/JogPad";
import { LedIndicator } from "../components/LedIndicator";
import { Popup } from "../components/Popup";
import { VersionBadge } from "../components/VersionBadge";
import type { DeckEventsState } from "../hooks/useDeckEvents";
import { CalendarWidget } from "../widgets/CalendarWidget";
import { JogWidget } from "../widgets/JogWidget";
import { LiveLogWidget } from "../widgets/LiveLogWidget";
import { NotesWidget } from "../widgets/NotesWidget";
import { OsdMockPanel } from "../widgets/OsdMockPanel";

import styles from "./HomePage.module.css";

export function HomePage({ deck }: { deck: DeckEventsState }) {
  const [osdOpen, setOsdOpen] = useState(false);
  // The popup must not close when clicking inside the JogPad column.
  const jogColRef = useRef<HTMLDivElement>(null);

  return (
    <div className={styles.page}>
      {deck.status && <VersionBadge version={deck.status.version} />}

      {/* Left column — JogPad + LED indicator */}
      <div className={styles.leftCol} ref={jogColRef} data-widget="jog-col">
        <div className={styles.ledCorner}>
          {/* Phase 15 wires this to blink events; Phase 13 stays grey by default. */}
          <LedIndicator on={false} />
        </div>

        {/* Recording lands in Phase 16; Phase 13 places the permanent control. */}
        <button
          className={styles.recordButton}
          type="button"
          aria-label="Record sequence (not yet active)"
          title="Record sequence - coming in Phase 16"
          onClick={() => {
            deck.pushLogLine("record — not wired yet");
          }}
        >
          <span className={styles.recordGlyph} aria-hidden="true" />
        </button>

        <JogWidget>
          <JogPad
            holdCounts={deck.holdCounts}
            wsReleaseTick={deck.wsReleaseTick}
            wsLastReleasedAction={deck.wsLastReleasedAction}
            wsSessionEpoch={deck.wsSessionEpoch}
            onLocalLog={deck.pushLogLine}
          />
        </JogWidget>

        {/* Dev trigger — Phase 15 replaces this with WebSocket bus events */}
        <button
          className={styles.osdTrigger}
          type="button"
          onClick={() => setOsdOpen(true)}
          aria-label="Show OSD mock"
          data-testid="osd-trigger"
          title="Dev: open OSD mock panel (Phase 15 wires this to bus events)"
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
        <LiveLogWidget lines={deck.logLines} />
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
    </div>
  );
}
