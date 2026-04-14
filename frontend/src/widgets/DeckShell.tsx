import type { ReactNode } from "react";

import styles from "./DeckShell.module.css";

/** Full-viewport appliance shell — no max-width “page”; content is the deck surface. */
export function DeckShell(props: { children: ReactNode }) {
  return (
    <div className={styles.shell} data-deck-root>
      {props.children}
    </div>
  );
}
