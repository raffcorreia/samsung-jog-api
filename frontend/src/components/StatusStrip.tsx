import type { StatusPayload } from "../types";

import styles from "./StatusStrip.module.css";

export function StatusStrip(props: {
  status: StatusPayload | null;
  wsConnected: boolean;
  wsError: string | null;
}) {
  const { status, wsConnected, wsError } = props;
  return (
    <header className={styles.bar} role="status">
      <div className={styles.title}>pi-deck</div>
      <div className={styles.meta}>
        {status ? (
          <>
            <span className={styles.pill} data-on={status.hardware === "live"}>
              {status.hardware}
            </span>
            <span className={styles.sep}>·</span>
            <span>{status.operating_mode}</span>
            <span className={styles.sep}>·</span>
            <span data-busy={status.control_state === "commanding"}>{status.control_state}</span>
            <span className={styles.sep}>·</span>
            <span className={styles.muted}>
              adc1 {status.signals.key_adc1_active ? "act" : "idle"} · led{" "}
              {status.signals.key_led_active ? "on" : "off"}
            </span>
            <span className={styles.sep}>·</span>
            <span className={styles.muted}>v{status.version}</span>
          </>
        ) : (
          <span className={styles.muted}>loading status…</span>
        )}
      </div>
      <div className={styles.ws} data-live={wsConnected}>
        ws {wsConnected ? "live" : "off"}
        {wsError ? <span className={styles.err}> ({wsError})</span> : null}
      </div>
    </header>
  );
}
