import { JogPad } from "./components/JogPad";
import { useDeckEvents } from "./hooks/useDeckEvents";
import { DeckShell } from "./widgets/DeckShell";
import { JogWidget } from "./widgets/JogWidget";
import { LiveLogWidget } from "./widgets/LiveLogWidget";
import { StatusBarWidget } from "./widgets/StatusBarWidget";

import styles from "./App.module.css";

export function App() {
  const deck = useDeckEvents();

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
            peerHeldActionCounts={deck.peerHeldActionCounts}
            onLocalLog={deck.pushLogLine}
            restHoldDownOk={deck.restHoldDownOk}
            restHoldUpOk={deck.restHoldUpOk}
          />
        </JogWidget>
        <LiveLogWidget lines={deck.logLines} />
      </div>
    </DeckShell>
  );
}
