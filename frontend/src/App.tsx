import { useMemo } from "react";

import { ConsoleHero } from "./components/ConsoleHero";
import { JogPad } from "./components/JogPad";
import { LiveLog } from "./components/LiveLog";
import { StatusStrip } from "./components/StatusStrip";
import { useDeckEvents } from "./hooks/useDeckEvents";

import styles from "./App.module.css";

export function App() {
  const deck = useDeckEvents();
  const busy = useMemo(
    () => deck.status?.control_state === "commanding",
    [deck.status?.control_state],
  );

  return (
    <div className={styles.app}>
      <ConsoleHero />
      <StatusStrip status={deck.status} wsConnected={deck.wsConnected} wsError={deck.wsError} />
      <main className={styles.main}>
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Controls</h2>
          <JogPad disabled={busy} onLocalLog={deck.pushLogLine} />
        </div>
      </main>
      <LiveLog lines={deck.logLines} />
    </div>
  );
}
