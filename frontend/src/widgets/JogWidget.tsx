import type { ReactNode } from "react";

import { DECK_WIDGETS } from "./deckWidgets";

import styles from "./JogWidget.module.css";

/** JOG region — no nested title chrome beyond the jog widget hero. */
export function JogWidget(props: { children: ReactNode }) {
  return (
    <div className={styles.slot} data-widget={DECK_WIDGETS.jog}>
      {props.children}
    </div>
  );
}
