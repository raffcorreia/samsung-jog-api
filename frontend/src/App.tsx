import { JogPad } from "./components/JogPad";
import { VersionBadge } from "./components/VersionBadge";
import { useDeckEvents } from "./hooks/useDeckEvents";
import { DeckShell } from "./widgets/DeckShell";
import { JogWidget } from "./widgets/JogWidget";
import { LiveLogWidget } from "./widgets/LiveLogWidget";

import styles from "./App.module.css";

export function App() {
  const deck = useDeckEvents();

  return (
    <DeckShell>
      {deck.status && <VersionBadge version={deck.status.version} />}
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
