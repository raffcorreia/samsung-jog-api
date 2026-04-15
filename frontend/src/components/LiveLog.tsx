import { memo, useEffect, useRef } from "react";

import styles from "./LiveLog.module.css";

function liveLogPropsEqual(
  prev: { lines: readonly string[] },
  next: { lines: readonly string[] },
): boolean {
  if (prev.lines === next.lines) {
    return true;
  }
  if (prev.lines.length !== next.lines.length) {
    return false;
  }
  for (let i = 0; i < prev.lines.length; i++) {
    if (prev.lines[i] !== next.lines[i]) {
      return false;
    }
  }
  return true;
}

function LiveLogInner(props: { lines: readonly string[] }) {
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

/** Memoized so parent re-renders that only touch the jog pad do not rebuild the log <pre> body. */
export const LiveLog = memo(LiveLogInner, liveLogPropsEqual);
