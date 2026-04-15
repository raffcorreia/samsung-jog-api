import { JogPad } from "./components/JogPad";
import { useDeckEvents } from "./hooks/useDeckEvents";
import { DeckShell } from "./widgets/DeckShell";
import { JogWidget } from "./widgets/JogWidget";
import { LiveLogWidget } from "./widgets/LiveLogWidget";

import styles from "./App.module.css";

export function App() {
  const deck = useDeckEvents();

  return (
    <DeckShell>
      <div className={styles.deckBody}>
        <JogWidget>
          <JogPad
            holdCounts={deck.holdCounts}
            wsReleaseTick={deck.wsReleaseTick}
            wsLastReleasedAction={deck.wsLastReleasedAction}
            wsSessionEpoch={deck.wsSessionEpoch}
            onLocalLog={deck.pushLogLine}
          />
        </JogWidget>
        <LiveLogWidget lines={deck.logLines} />
      </div>
    </DeckShell>
  );
}
