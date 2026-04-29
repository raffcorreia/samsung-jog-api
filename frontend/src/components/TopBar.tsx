import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchDisplayPower, setDisplayPower } from "../api/client";
import { PowerMenu } from "./PowerMenu";

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
 * Power button (Phase 19):
 *   - If display is on  → opens PowerMenu (Display off / Pi shutdown / Cancel).
 *   - If display is off → powers the display back on immediately (remote browser use-case).
 */
export function TopBar({ title }: { title?: string }) {
  const navigate = useNavigate();
  const isHome = !title;

  const [displayOn, setDisplayOn] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

  // Fetch initial display power state once on mount.
  useEffect(() => {
    fetchDisplayPower()
      .then((p) => setDisplayOn(p.on))
      .catch(() => {
        /* best-effort; display on is the safe default */
      });
  }, []);

  async function handlePowerClick() {
    // Always fetch fresh state before acting — avoids stale-cache opening the
    // wrong branch (e.g. menu when display is already off, or vice-versa).
    let on = displayOn;
    try {
      const state = await fetchDisplayPower();
      on = state.on;
      setDisplayOn(on);
    } catch {
      /* use cached state if the fetch fails */
    }

    if (!on) {
      // Display is off — power it back on immediately.
      try {
        const result = await setDisplayPower(true);
        setDisplayOn(result.on);
      } catch {
        /* network error while display is off; nothing actionable */
      }
    } else {
      setMenuOpen(true);
    }
  }

  function handleDisplayToggled() {
    // Re-fetch after the menu performs a toggle.
    fetchDisplayPower()
      .then((p) => setDisplayOn(p.on))
      .catch(() => {});
  }

  return (
    <>
      <header className={styles.bar} data-testid="top-bar">
        <div className={styles.left}>
          <button
            className={`${styles.powerBtn}${displayOn ? "" : ` ${styles.powerBtnOff}`}`}
            type="button"
            aria-label={displayOn ? "Power menu" : "Turn display on"}
            data-testid="top-bar-power"
            onClick={() => void handlePowerClick()}
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

      <PowerMenu
        open={menuOpen}
        displayOn={displayOn}
        onClose={() => setMenuOpen(false)}
        onDisplayToggled={handleDisplayToggled}
      />
    </>
  );
}
