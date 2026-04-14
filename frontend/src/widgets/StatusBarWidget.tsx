import { StatusStrip } from "../components/StatusStrip";
import type { StatusPayload } from "../types";

import { DECK_WIDGETS } from "./deckWidgets";

import styles from "./StatusBarWidget.module.css";

export function StatusBarWidget(props: {
  status: StatusPayload | null;
  wsConnected: boolean;
  wsError: string | null;
}) {
  return (
    <div className={styles.wrap} data-widget={DECK_WIDGETS.status}>
      <StatusStrip
        status={props.status}
        wsConnected={props.wsConnected}
        wsError={props.wsError}
      />
    </div>
  );
}
