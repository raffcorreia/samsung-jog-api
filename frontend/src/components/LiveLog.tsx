import { useEffect, useRef } from "react";

import styles from "./LiveLog.module.css";

export function LiveLog(props: { lines: readonly string[] }) {
  const endRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [props.lines.length]);

  return (
    <section className={styles.wrap} aria-label="Live log">
      <div className={styles.head}>Live log</div>
      <pre className={styles.pre} role="log">
        {props.lines.length === 0 ? (
          <span className={styles.placeholder}>Waiting for events…</span>
        ) : (
          props.lines.map((line, i) => (
            <div key={`${i}-${line.slice(0, 24)}`} className={styles.line}>
              {line}
            </div>
          ))
        )}
        <div ref={endRef} />
      </pre>
    </section>
  );
}
