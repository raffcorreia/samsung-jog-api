/**
 * Power menu — opened from the TopBar power button.
 *
 * Phase 22 scope:
 *   Display: power off/on the DSI backlight immediately.
 *   Reset:   10-second countdown → reboot.
 *   Power off: confirmation screen → 10-second countdown → halt.
 *   Cancel: close without action.
 *
 * When the display is already off the power button (pressed from a remote
 * browser) powers it back on instead of opening this menu.
 */
import { useEffect, useRef, useState } from "react";

import { requestRestart, requestShutdown, setDisplayPower } from "../api/client";
import { ConfirmDialog } from "./ConfirmDialog";
import { Popup } from "./Popup";

import styles from "./PowerMenu.module.css";

const COUNTDOWN_S = 10;

interface PowerMenuProps {
  open: boolean;
  displayOn: boolean;
  onClose: () => void;
  /** Called after a display power toggle completes so parent can refresh state. */
  onDisplayToggled?: () => void;
}

type View = "menu" | "poweroff_confirm" | "countdown";
type CountdownAction = "reset" | "poweroff";

export function PowerMenu({ open, displayOn, onClose, onDisplayToggled }: PowerMenuProps) {
  const [view, setView] = useState<View>("menu");
  const [countdownAction, setCountdownAction] = useState<CountdownAction>("poweroff");
  const [countdown, setCountdown] = useState(COUNTDOWN_S);
  const [busy, setBusy] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!open) {
      setView("menu");
      setCountdown(COUNTDOWN_S);
      setBusy(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      if (view === "countdown") {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        setView("menu");
        setCountdown(COUNTDOWN_S);
      } else if (view === "poweroff_confirm") {
        setView("menu");
      } else {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, view, onClose]);

  useEffect(() => {
    if (view !== "countdown" || !open) return;

    setCountdown(COUNTDOWN_S);
    intervalRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(intervalRef.current!);
          intervalRef.current = null;
          void executeAction();
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
      // Best-effort; error is already logged server-side
    }
  }

  function startCountdown(action: CountdownAction) {
    setCountdownAction(action);
    setView("countdown");
  }

  async function executeAction() {
    if (busy) return;
    setBusy(true);
    try {
      if (countdownAction === "reset") {
        await requestRestart();
      } else {
        await requestShutdown();
      }
    } catch {
      // Pi going offline causes a network error — expected
    }
    onClose();
  }

  function cancelCountdown() {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setView("menu");
    setCountdown(COUNTDOWN_S);
  }

  const isReset = countdownAction === "reset";

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

          <div className={styles.smallActions}>
            <button
              className={styles.smallBtn}
              data-testid="power-menu-reset"
              type="button"
              onClick={() => startCountdown("reset")}
            >
              Restart
            </button>
            <button
              className={`${styles.smallBtn} ${styles.smallBtnDanger}`}
              data-testid="power-menu-poweroff"
              type="button"
              onClick={() => setView("poweroff_confirm")}
            >
              Power off
            </button>
          </div>

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

      {/* Power off danger confirmation */}
      <ConfirmDialog
        open={open && view === "poweroff_confirm"}
        title="Power off?"
        message="The deck cannot be restored without physically unplugging and replugging the power cable."
        confirmLabel="Continue"
        cancelLabel="Cancel"
        onConfirm={() => startCountdown("poweroff")}
        onCancel={() => setView("menu")}
      />

      {/* Shared countdown screen — used by both Reset and Power off */}
      <Popup
        open={open && view === "countdown"}
        onClose={cancelCountdown}
        position="center"
        size="confirm"
        title={isReset ? "Restart Pi?" : "Shut down Pi?"}
        blockBackground
      >
        <div className={styles.shutdownBody}>
          <p className={styles.countdownText}>
            {isReset ? "Restarting in" : "Shutting down in"}{" "}
            <strong data-testid="action-countdown">{countdown}</strong>…
          </p>
          <div className={styles.shutdownActions}>
            <button
              className={styles.cancelBtn}
              type="button"
              disabled={busy}
              onClick={cancelCountdown}
              data-testid="countdown-cancel"
            >
              Cancel
            </button>
            <button
              className={styles.shutdownNowBtn}
              type="button"
              disabled={busy}
              onClick={() => void executeAction()}
              data-testid="countdown-now"
            >
              {isReset ? "Restart now" : "Shut down now"}
            </button>
          </div>
        </div>
      </Popup>
    </>
  );
}
