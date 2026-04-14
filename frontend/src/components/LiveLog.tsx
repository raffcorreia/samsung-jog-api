import { useEffect, useRef } from "react";

import styles from "./LiveLog.module.css";

export function LiveLog(props: { lines: readonly string[] }) {
  const preRef = useRef<HTMLPreElement | null>(null);
  const { lines } = props;
  const body = lines.join("\n");
  useEffect(() => {
    const el = preRef.current;
    if (!el || lines.length === 0) {
      return;
    }
    el.scrollTop = el.scrollHeight;
  }, [lines.length, body]);

  return (
    <section className={styles.wrap} aria-label="Live log">
      <div className={styles.head}>Live log</div>
      <pre ref={preRef} className={styles.pre} role="log">
        {lines.length === 0 ? (
          <span className={styles.placeholder}>Waiting for events…</span>
        ) : (
          body
        )}
      </pre>
    </section>
  );
}
