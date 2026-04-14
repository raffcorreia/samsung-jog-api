import { useRef } from "react";

import { JogPad, type JogPadHandle } from "./components/JogPad";
import { useDeckEvents } from "./hooks/useDeckEvents";
import { DeckShell } from "./widgets/DeckShell";
import { JogWidget } from "./widgets/JogWidget";
import { LiveLogWidget } from "./widgets/LiveLogWidget";
import { StatusBarWidget } from "./widgets/StatusBarWidget";

import styles from "./App.module.css";

export function App() {
  const jogPadRef = useRef<JogPadHandle>(null);
  const deck = useDeckEvents(jogPadRef);

  return (
    <DeckShell>
      <StatusBarWidget
        status={deck.status}
        wsConnected={deck.wsConnected}
        wsError={deck.wsError}
      />
      <div className={styles.deckBody}>
        <JogWidget>
          <JogPad
            ref={jogPadRef}
            peerHeldActionCounts={deck.peerHeldActionCounts}
            onLocalLog={deck.pushLogLine}
            restHoldOk={deck.restHoldOk}
            restReleaseOk={deck.restReleaseOk}
          />
        </JogWidget>
        <LiveLogWidget lines={deck.logLines} />
      </div>
    </DeckShell>
  );
}
