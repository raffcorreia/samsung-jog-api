import { useMemo } from "react";

import { JogPad } from "./components/JogPad";
import { useDeckEvents } from "./hooks/useDeckEvents";
import { DeckShell } from "./widgets/DeckShell";
import { JogWidget } from "./widgets/JogWidget";
import { LiveLogWidget } from "./widgets/LiveLogWidget";
import { StatusBarWidget } from "./widgets/StatusBarWidget";

import styles from "./App.module.css";

export function App() {
  const deck = useDeckEvents();
  const busy = useMemo(
    () => deck.status?.control_state === "commanding",
    [deck.status?.control_state],
  );

  return (
    <DeckShell>
      <StatusBarWidget
        status={deck.status}
        wsConnected={deck.wsConnected}
        wsError={deck.wsError}
      />
      <div className={styles.deckBody}>
        <JogWidget>
          <JogPad deckBusy={busy} onLocalLog={deck.pushLogLine} />
        </JogWidget>
        <LiveLogWidget lines={deck.logLines} />
      </div>
    </DeckShell>
  );
}
