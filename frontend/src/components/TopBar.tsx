import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import styles from "./TopBar.module.css";

function formatTime(d: Date): string {
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${h}:${m}`;
}

function Clock() {
  const [time, setTime] = useState(() => formatTime(new Date()));
  useEffect(() => {
    const id = setInterval(() => setTime(formatTime(new Date())), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <time className={styles.clock} dateTime={time} data-testid="top-bar-clock">
      {time}
    </time>
  );
}

/**
 * Persistent top bar — visible on every screen.
 *
 * - Home (no title): shows only power, clock, and settings cog.
 * - Other screens (title provided): shows back arrow + title in the centre section.
 *
 * Power button: stub — Phase 20 wires display power.
 */
export function TopBar({ title }: { title?: string }) {
  const navigate = useNavigate();
  const isHome = !title;

  return (
    <header className={styles.bar} data-testid="top-bar">
      <div className={styles.left}>
        {/* Power stub — Phase 20 */}
        <button
          className={styles.powerBtn}
          type="button"
          aria-label="Power (not yet active)"
          title="Display power — coming in Phase 20"
          onClick={() => {
            /* stub */
          }}
        >
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 2v10" />
            <path d="M8.56 5a8 8 0 1 0 6.88 0" />
          </svg>
        </button>

        <Clock />
      </div>

      {!isHome && (
        <div className={styles.center}>
          <button
            className={styles.backBtn}
            type="button"
            aria-label="Back to home"
            title="Back to home"
            onClick={() => navigate("/")}
            data-testid="top-bar-back"
          >
            <svg
              viewBox="0 0 24 24"
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M19 12H5" />
              <path d="M12 5l-7 7 7 7" />
            </svg>
          </button>
          <h1 className={styles.title} data-testid="top-bar-title">
            {title}
          </h1>
        </div>
      )}

      <div className={styles.right}>
        <button
          className={styles.cogBtn}
          type="button"
          aria-label="Settings"
          data-testid="top-bar-settings"
          onClick={() => navigate("/settings")}
        >
          <svg
            viewBox="0 0 24 24"
            width="20"
            height="20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
          </svg>
        </button>
      </div>
    </header>
  );
}
