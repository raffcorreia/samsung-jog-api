/**
 * Power menu — opened from the TopBar power button.
 *
 * Phase 19 scope:
 *   Display: power off the DSI backlight immediately.
 *   Pi:      open a secondary confirmation with a 5-second countdown.
 *   Cancel:  close without action.
 *
 * When the display is already off the power button (pressed from a remote
 * browser) powers it back on instead of opening this menu.
 */
import { useEffect, useRef, useState } from "react";

import { requestShutdown, setDisplayPower } from "../api/client";
import { Popup } from "./Popup";

import styles from "./PowerMenu.module.css";

const SHUTDOWN_COUNTDOWN_S = 5;

interface PowerMenuProps {
  open: boolean;
  displayOn: boolean;
  onClose: () => void;
  /** Called after a display power toggle completes so parent can refresh state. */
  onDisplayToggled?: () => void;
}

type View = "menu" | "shutdown_confirm";

export function PowerMenu({ open, displayOn, onClose, onDisplayToggled }: PowerMenuProps) {
  const [view, setView] = useState<View>("menu");
  const [countdown, setCountdown] = useState(SHUTDOWN_COUNTDOWN_S);
  const [shutdownBusy, setShutdownBusy] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Reset internal state whenever the popup opens/closes.
  useEffect(() => {
    if (!open) {
      setView("menu");
      setCountdown(SHUTDOWN_COUNTDOWN_S);
      setShutdownBusy(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [open]);

  // Start countdown when shutdown confirm view is shown.
  useEffect(() => {
    if (view !== "shutdown_confirm" || !open) return;

    setCountdown(SHUTDOWN_COUNTDOWN_S);
    intervalRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(intervalRef.current!);
          intervalRef.current = null;
          void doShutdown();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, open]);

  async function handleDisplayToggle() {
    onClose();
    try {
      await setDisplayPower(!displayOn);
      onDisplayToggled?.();
    } catch {
      // Best-effort; log is already server-side
    }
  }

  function handlePiChoice() {
    setView("shutdown_confirm");
  }

  async function doShutdown() {
    if (shutdownBusy) return;
    setShutdownBusy(true);
    try {
      await requestShutdown();
    } catch {
      // Pi will go offline; network error is expected
    }
    onClose();
  }

  function handleCancelShutdown() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setView("menu");
    setCountdown(SHUTDOWN_COUNTDOWN_S);
  }

  return (
    <>
      {/* Primary power menu */}
      <Popup
        open={open && view === "menu"}
        onClose={onClose}
        position="center"
        size="confirm"
        title="Power"
        blockBackground
      >
        <div className={styles.body}>
          <button
            className={styles.choiceBtn}
            data-testid="power-menu-display"
            type="button"
            onClick={() => void handleDisplayToggle()}
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
              <rect x="2" y="3" width="20" height="14" rx="2" />
              <path d="M8 21h8M12 17v4" />
            </svg>
            <span>{displayOn ? "Display off" : "Display on"}</span>
          </button>

          <button
            className={styles.choiceBtn}
            data-testid="power-menu-pi"
            type="button"
            onClick={handlePiChoice}
          >
            {/* Raspberry Pi logo simplified */}
            <svg
              viewBox="0 0 24 24"
              width="20"
              height="20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zm0 3a7 7 0 1 1 0 14A7 7 0 0 1 12 5zm0 2a5 5 0 1 0 0 10A5 5 0 0 0 12 7zm0 2a3 3 0 1 1 0 6 3 3 0 0 1 0-6z" />
            </svg>
            <span>Shut down Pi</span>
          </button>

          <button
            className={`${styles.choiceBtn} ${styles.cancel}`}
            data-testid="power-menu-cancel"
            type="button"
            onClick={onClose}
          >
            Cancel
          </button>
        </div>
      </Popup>

      {/* Secondary shutdown confirmation */}
      <Popup
        open={open && view === "shutdown_confirm"}
        onClose={handleCancelShutdown}
        position="center"
        size="confirm"
        title="Shut down Pi?"
        blockBackground
      >
        <div className={styles.shutdownBody}>
          <p className={styles.countdownText}>
            Shutting down in <strong data-testid="shutdown-countdown">{countdown}</strong>…
          </p>
          <div className={styles.shutdownActions}>
            <button
              className={styles.cancelBtn}
              type="button"
              disabled={shutdownBusy}
              onClick={handleCancelShutdown}
              data-testid="shutdown-cancel"
            >
              Cancel
            </button>
            <button
              className={styles.shutdownNowBtn}
              type="button"
              disabled={shutdownBusy}
              onClick={() => void doShutdown()}
              data-testid="shutdown-now"
            >
              Now
            </button>
          </div>
        </div>
      </Popup>
    </>
  );
}
