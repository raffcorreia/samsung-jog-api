import { LiveLog } from "../components/LiveLog";

import { DECK_WIDGETS } from "./deckWidgets";

import styles from "./LiveLogWidget.module.css";

export function LiveLogWidget(props: { lines: readonly string[] }) {
  return (
    <section className={styles.widget} data-widget={DECK_WIDGETS.log} aria-label="Event log">
      <LiveLog lines={props.lines} />
    </section>
  );
}
