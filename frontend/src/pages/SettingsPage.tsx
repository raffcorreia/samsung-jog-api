import { DECK_WIDGETS } from "../widgets/deckWidgets";
import styles from "./SettingsPage.module.css";

/**
 * Settings page — stub for Phase 13.
 *
 * Phase 13 scope: routing and navigation only. Content will be added in later
 * phases (theme toggle, widget visibility, operating mode preference, etc.).
 */
export function SettingsPage() {
  return (
    <div className={styles.page} data-widget={DECK_WIDGETS.settings}>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Appearance</h2>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Theme</span>
          <span className={styles.rowValue}>Dark</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Show live log</span>
          <span className={styles.rowValue}>On</span>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Control</h2>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Default operating mode</span>
          <span className={styles.rowValue}>JOG</span>
        </div>
        <div className={styles.row}>
          <span className={styles.rowLabel}>Hardware mode</span>
          <span className={styles.rowValue}>Live</span>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>About</h2>
        <div className={styles.row}>
          <span className={styles.rowLabel}>pi-deck</span>
          <span className={styles.rowValue}>Settings coming in a future phase</span>
        </div>
      </section>
    </div>
  );
}
