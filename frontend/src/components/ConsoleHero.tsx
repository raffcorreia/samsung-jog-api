import styles from "./ConsoleHero.module.css";

/** Visible product chrome — makes it obvious this is the real deck UI, not a placeholder page. */
export function ConsoleHero() {
  return (
    <section className={styles.hero} aria-labelledby="jog-console-title">
      <p className={styles.eyebrow}>Samsung CJ791 · low-level control</p>
      <h1 id="jog-console-title" className={styles.title}>
        JOG console
      </h1>
      <p className={styles.lede}>
        Press or hold directional and center keys; the deck sends timed jog commands to the monitor. Status
        and hardware events update live below — same page in kiosk or from your browser on the LAN.
      </p>
    </section>
  );
}
