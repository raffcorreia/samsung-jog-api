import { memo, useCallback, useEffect, useRef, useState } from "react";

import styles from "./LiveLog.module.css";

export type LiveLogProps = {
  lines: readonly string[];
  onClearServerLog: () => Promise<void>;
};

/** HTTP (e.g. http://10.x on the Pi kiosk) is not a "secure context", so Clipboard API often fails. */
function copyTextFallback(text: string): boolean {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.left = "-9999px";
  ta.style.top = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  ta.setSelectionRange(0, text.length);
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } finally {
    document.body.removeChild(ta);
  }
  return ok;
}

async function copyTextToClipboard(text: string): Promise<boolean> {
  /* LAN HTTP (Pi kiosk) is not a secure context — Clipboard API is blocked; use fallback immediately
   * so execCommand runs in the same user-gesture turn as the click. */
  if (typeof window !== "undefined" && !window.isSecureContext) {
    return copyTextFallback(text);
  }
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return copyTextFallback(text);
    }
  }
  return copyTextFallback(text);
}

function liveLogPropsEqual(prev: LiveLogProps, next: LiveLogProps): boolean {
  if (prev.onClearServerLog !== next.onClearServerLog) {
    return false;
  }
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

function LiveLogInner(props: LiveLogProps) {
  const preRef = useRef<HTMLPreElement | null>(null);
  const { lines, onClearServerLog } = props;
  const body = lines.join("\n");
  const [clearBusy, setClearBusy] = useState(false);

  useEffect(() => {
    const el = preRef.current;
    if (!el || lines.length === 0) {
      return;
    }
    el.scrollTop = el.scrollHeight;
  }, [lines.length, body]);

  const handleCopy = useCallback(async () => {
    if (lines.length === 0) {
      return;
    }
    await copyTextToClipboard(body);
  }, [body, lines.length]);

  const handleClear = useCallback(async () => {
    if (clearBusy) {
      return;
    }
    setClearBusy(true);
    try {
      await onClearServerLog();
    } finally {
      setClearBusy(false);
    }
  }, [clearBusy, onClearServerLog]);

  return (
    <section className={styles.wrap} aria-label="Live log">
      <div className={styles.head}>
        <span className={styles.headTitle}>Live log</span>
        <div className={styles.headActions}>
          <button
            type="button"
            className={styles.toolBtn}
            onClick={() => void handleCopy()}
            disabled={lines.length === 0}
            aria-label="Copy full log to clipboard"
            title="Copy all lines"
          >
            <svg
              className={styles.toolIcon}
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <rect x="8" y="8" width="12" height="12" rx="2" />
              <path d="M4 16V6a2 2 0 0 1 2-2h10" />
            </svg>
          </button>
          <button
            type="button"
            className={styles.toolBtn}
            onClick={() => void handleClear()}
            disabled={clearBusy}
            aria-busy={clearBusy}
            aria-label="Clear log on server"
            title="Delete server log buffer"
          >
            {clearBusy ? (
              <svg
                className={`${styles.toolIcon} ${styles.toolIconSpin}`}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="M21 12a9 9 0 1 1-3.82-7.36" />
              </svg>
            ) : (
              <svg
                className={styles.toolIcon}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M3 6h18" />
                <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                <path d="M10 11v6M14 11v6" />
              </svg>
            )}
          </button>
        </div>
      </div>
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
