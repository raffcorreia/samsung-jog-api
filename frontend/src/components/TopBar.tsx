import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { setDisplayPower } from "../api/client";
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
export function TopBar({
  title,
  openPowerMenuTick = 0,
  displayOn = true,
  powerButtonHeld = false,
}: {
  title?: string;
  openPowerMenuTick?: number;
  displayOn?: boolean;
  powerButtonHeld?: boolean;
}) {
  const navigate = useNavigate();
  const isHome = !title;

  const [menuOpen, setMenuOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [localHeld, setLocalHeld] = useState(false);
  const holdTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const holdFiredRef = useRef(false);

  useEffect(() => {
    return () => {
      if (holdTimerRef.current) clearTimeout(holdTimerRef.current);
    };
  }, []);

  // Physical button short-press → open the power menu (display is already on when this fires).
  useEffect(() => {
    if (openPowerMenuTick === 0) return;
    setMenuOpen(true);
  }, [openPowerMenuTick]);

  async function handlePowerClick() {
    if (!displayOn) {
      // Display is off — power it back on immediately.
      setPending(true);
      try {
        await Promise.all([
          setDisplayPower(true),
          new Promise((r) => setTimeout(r, 3000)),
        ]);
      } catch {
        /* network error while display is off; nothing actionable */
      } finally {
        setPending(false);
      }
    } else {
      setMenuOpen(true);
    }
  }

  function handleDisplayToggled() {
    // WS display/power_changed event handles state sync.
  }

  function handlePointerDown() {
    holdFiredRef.current = false;
    if (!displayOn) return; // display off: handle on pointer up (turn on)
    setLocalHeld(true);
    holdTimerRef.current = setTimeout(() => {
      holdFiredRef.current = true;
      holdTimerRef.current = null;
      setLocalHeld(false);
      // Hold 3 s → turn display off directly
      setPending(true);
      setDisplayPower(false)
        .catch(() => {})
        .finally(() => setPending(false));
    }, 3000);
  }

  function handlePointerUp() {
    setLocalHeld(false);
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }
    if (!holdFiredRef.current) {
      void handlePowerClick();
    }
  }

  function handlePointerLeave() {
    setLocalHeld(false);
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
      holdFiredRef.current = false;
    }
  }

  return (
    <>
      <header className={styles.bar} data-testid="top-bar">
        <div className={styles.left}>
          <button
            className={`${styles.powerBtn}${powerButtonHeld || localHeld ? ` ${styles.powerBtnAmber}` : displayOn ? ` ${styles.powerBtnOn}` : ""}`}
            type="button"
            aria-label={displayOn ? "Power menu" : "Turn display on"}
            data-testid="top-bar-power"
            onPointerDown={handlePointerDown}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerLeave}
          >
            {pending ? (
              <svg
                className={styles.spinner}
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="M12 2a10 10 0 1 0 10 10" />
              </svg>
            ) : (
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
            )}
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
