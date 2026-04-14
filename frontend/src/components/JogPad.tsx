import { useCallback, useRef, useState, type PointerEvent } from "react";

import { jogPress } from "../api/client";
import type { JogAction } from "../types";

import styles from "./JogPad.module.css";

const TAP_MIN_MS = 1;
const TAP_MAX_MS = 60_000;

function clampDuration(ms: number): number {
  const n = Math.round(ms);
  return Math.min(TAP_MAX_MS, Math.max(TAP_MIN_MS, n));
}

export function JogPad(props: {
  disabled?: boolean;
  onLocalLog: (line: string) => void;
}) {
  const { disabled, onLocalLog } = props;
  const [active, setActive] = useState<JogAction | null>(null);
  const startRef = useRef<number | null>(null);
  const actionRef = useRef<JogAction | null>(null);

  const endHold = useCallback(
    async (action: JogAction) => {
      const started = startRef.current;
      startRef.current = null;
      actionRef.current = null;
      setActive(null);
      if (started == null) {
        return;
      }
      const durationMs = clampDuration(performance.now() - started);
      try {
        const result = await jogPress(action, durationMs);
        if (!result.ok) {
          onLocalLog(
            `http rejected — ${result.body.reason}: ${result.body.message}`,
          );
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        onLocalLog(`jog request failed — ${msg}`);
      }
    },
    [onLocalLog],
  );

  const onPointerDown = (action: JogAction) => (ev: PointerEvent<HTMLButtonElement>) => {
    if (disabled) {
      return;
    }
    ev.preventDefault();
    ev.currentTarget.setPointerCapture?.(ev.pointerId);
    startRef.current = performance.now();
    actionRef.current = action;
    setActive(action);
  };

  const onPointerUp = (action: JogAction) => (ev: PointerEvent<HTMLButtonElement>) => {
    if (disabled) {
      return;
    }
    ev.preventDefault();
    try {
      ev.currentTarget.releasePointerCapture?.(ev.pointerId);
    } catch {
      /* ignore */
    }
    if (actionRef.current !== action) {
      return;
    }
    void endHold(action);
  };

  const onPointerCancel = (action: JogAction) => () => {
    if (actionRef.current !== action) {
      return;
    }
    void endHold(action);
  };

  const Btn = (p: { action: JogAction; label: string; className?: string }) => (
    <button
      type="button"
      className={p.className}
      disabled={disabled}
      aria-pressed={active === p.action}
      onPointerDown={onPointerDown(p.action)}
      onPointerUp={onPointerUp(p.action)}
      onPointerCancel={onPointerCancel(p.action)}
      onLostPointerCapture={onPointerCancel(p.action)}
    >
      {p.label}
    </button>
  );

  return (
    <div className={styles.shell} data-testid="jog-pad" data-touch-policy="none">
      <div className={styles.grid}>
        <div className={styles.spacer} />
        <Btn action="up" label="Up" className={`${styles.btn} ${styles.up}`} />
        <div className={styles.spacer} />
        <Btn action="left" label="Left" className={`${styles.btn} ${styles.left}`} />
        <Btn action="center" label="OK" className={`${styles.btn} ${styles.center}`} />
        <Btn action="right" label="Right" className={`${styles.btn} ${styles.right}`} />
        <div className={styles.spacer} />
        <Btn action="down" label="Down" className={`${styles.btn} ${styles.down}`} />
        <div className={styles.spacer} />
      </div>
      <p className={styles.hint}>Press or hold — duration is sent as one timed jog assertion.</p>
    </div>
  );
}
