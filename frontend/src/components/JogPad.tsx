import { memo, useCallback, useEffect, useRef, useState, type PointerEvent } from "react";

import { jogHold, releaseJog } from "../api/client";
import type { JogAction } from "../types";

import { annulusSectorPath } from "./jogGeometry";

import styles from "./JogPad.module.css";

const VB = 200;
const CX = 100;
const CY = 100;
const R_OUT = 92;
const R_IN = 46;
const SECTORS: Record<Exclude<JogAction, "center">, { start: number; end: number }> = {
  up: { start: 226, end: 314 },
  right: { start: 316, end: 44 },
  down: { start: 46, end: 134 },
  left: { start: 136, end: 224 },
};

const SEGMENT_LABELS: Record<JogAction, string> = {
  up: "Up",
  down: "Down",
  left: "Left",
  right: "Right",
  center: "Enter",
};

function sectorPath(action: Exclude<JogAction, "center">): string {
  const { start, end } = SECTORS[action];
  return annulusSectorPath(CX, CY, R_IN, R_OUT, start, end);
}

function readJogAction(ev: PointerEvent<Element>): JogAction | null {
  let el: HTMLElement | null = ev.target as HTMLElement | null;
  for (let i = 0; i < 8 && el; i++) {
    const a = el.getAttribute("data-jog-action");
    if (
      a === "up" ||
      a === "down" ||
      a === "left" ||
      a === "right" ||
      a === "center"
    ) {
      return a;
    }
    el = el.parentElement;
  }
  return null;
}

type PtrState = {
  action: JogAction;
  holdEstablished: boolean;
  downPromise: Promise<void>;
  releaseInFlight: boolean;
};

function isHeldOnWire(
  hardwareHeld: Record<JogAction, boolean>,
  action: JogAction,
): boolean {
  return hardwareHeld[action] ?? false;
}

function emptyOptimistic(): Record<JogAction, boolean> {
  return {
    up: false,
    down: false,
    left: false,
    right: false,
    center: false,
  };
}

function JogPadInner(props: {
  hardwareHeld: Record<JogAction, boolean>;
  wsReleaseTick: number;
  wsLastReleasedAction: JogAction | null;
  wsSessionEpoch: number;
  onLocalLog: (line: string) => void;
}) {
  const { hardwareHeld, wsReleaseTick, wsLastReleasedAction, wsSessionEpoch, onLocalLog } = props;
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const ptrMapRef = useRef(new Map<number, PtrState>());
  const [optimistic, setOptimistic] = useState(() => emptyOptimistic());

  /* New websocket session (including first ``connected``): clear stale pointer holds. */
  useEffect(() => {
    for (const rec of ptrMapRef.current.values()) {
      rec.holdEstablished = false;
    }
    setOptimistic(emptyOptimistic());
  }, [wsSessionEpoch]);

  /* Drop optimistic overlay once observation stream confirms the hold. */
  useEffect(() => {
    setOptimistic((prev) => {
      let next = prev;
      for (const a of Object.keys(prev) as JogAction[]) {
        if (prev[a] && isHeldOnWire(hardwareHeld, a)) {
          if (next === prev) {
            next = { ...prev };
          }
          next[a] = false;
        }
      }
      return next;
    });
  }, [hardwareHeld]);

  /* Observation shows release (peer / watchdog): drop matching pointer hold so pointer-up does not send a bogus release. */
  useEffect(() => {
    if (wsReleaseTick === 0) {
      return;
    }
    const a = wsLastReleasedAction;
    if (!a) {
      return;
    }
    for (const rec of ptrMapRef.current.values()) {
      if (rec.action === a && rec.holdEstablished) {
        rec.holdEstablished = false;
      }
    }
  }, [wsReleaseTick, wsLastReleasedAction]);

  const releasePointer = useCallback(
    async (pointerId: number) => {
      const rec = ptrMapRef.current.get(pointerId);
      if (!rec) {
        return;
      }
      if (rec.releaseInFlight) {
        return;
      }
      rec.releaseInFlight = true;
      try {
        try {
          await rec.downPromise;
        } catch {
          /* ignore */
        }
        if (!rec.holdEstablished) {
          return;
        }
        const action = rec.action;
        try {
          const r = await releaseJog(action);
          if (!r.ok) {
            onLocalLog(`http jog/release — ${r.body.reason}: ${r.body.message}`);
          }
        } catch (e) {
          const msg = e instanceof Error ? e.message : String(e);
          onLocalLog(`jog release failed — ${msg}`);
        }
      } finally {
        ptrMapRef.current.delete(pointerId);
        rec.releaseInFlight = false;
      }
    },
    [onLocalLog],
  );

  const onSurfacePointerDown = (ev: PointerEvent<HTMLDivElement>) => {
    if (ev.button !== 0 && ev.button !== -1) {
      return;
    }
    const action = readJogAction(ev);
    if (!action) {
      return;
    }
    ev.preventDefault();
    ev.stopPropagation();

    const surf = surfaceRef.current;
    if (surf?.setPointerCapture) {
      try {
        surf.setPointerCapture(ev.pointerId);
      } catch {
        /* ignore */
      }
    }

    let resolveDown!: () => void;
    const downPromise = new Promise<void>((r) => {
      resolveDown = r;
    });

    const rec: PtrState = {
      action,
      holdEstablished: false,
      downPromise,
      releaseInFlight: false,
    };
    ptrMapRef.current.set(ev.pointerId, rec);

    void jogHold(action)
      .then((r) => {
        if (r.ok) {
          rec.holdEstablished = true;
          setOptimistic((o) => ({ ...o, [action]: true }));
        } else {
          onLocalLog(`http jog/hold — ${r.body.reason}: ${r.body.message}`);
        }
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : String(e);
        onLocalLog(`jog hold failed — ${msg}`);
      })
      .finally(() => {
        resolveDown();
      });
  };

  const onSurfacePointerUp = (ev: PointerEvent<HTMLDivElement>) => {
    const rec = ptrMapRef.current.get(ev.pointerId);
    if (!rec) {
      return;
    }
    ev.preventDefault();
    const surf = surfaceRef.current;
    if (surf?.releasePointerCapture) {
      try {
        surf.releasePointerCapture(ev.pointerId);
      } catch {
        /* ignore */
      }
    }
    void releasePointer(ev.pointerId);
  };

  const onSurfacePointerCancel = (ev: PointerEvent<HTMLDivElement>) => {
    const rec = ptrMapRef.current.get(ev.pointerId);
    if (!rec) {
      return;
    }
    void releasePointer(ev.pointerId);
  };

  return (
    <div className={styles.shell} data-testid="jog-pad" data-touch-policy="none">
      <div
        ref={surfaceRef}
        className={styles.surface}
        onPointerDown={onSurfacePointerDown}
        onPointerUp={onSurfacePointerUp}
        onPointerCancel={onSurfacePointerCancel}
      >
        <svg
          className={styles.ringSvg}
          viewBox={`0 0 ${VB} ${VB}`}
          width="100%"
          height="100%"
          aria-hidden
        >
          <path
            className={`${styles.ringSeg} ${styles.segUp}`}
            d={sectorPath("up")}
            data-jog-action="up"
            role="button"
            tabIndex={0}
            aria-label={`Jog ${SEGMENT_LABELS.up}`}
            aria-pressed={
              isHeldOnWire(hardwareHeld, "up") || optimistic.up
            }
            data-pressed={
              isHeldOnWire(hardwareHeld, "up") || optimistic.up ? "true" : undefined
            }
            data-optimistic={
              optimistic.up && !isHeldOnWire(hardwareHeld, "up") ? "true" : undefined
            }
          />
          <path
            className={`${styles.ringSeg} ${styles.segRight}`}
            d={sectorPath("right")}
            data-jog-action="right"
            role="button"
            tabIndex={0}
            aria-label={`Jog ${SEGMENT_LABELS.right}`}
            aria-pressed={isHeldOnWire(hardwareHeld, "right") || optimistic.right}
            data-pressed={
              isHeldOnWire(hardwareHeld, "right") || optimistic.right ? "true" : undefined
            }
            data-optimistic={
              optimistic.right && !isHeldOnWire(hardwareHeld, "right") ? "true" : undefined
            }
          />
          <path
            className={`${styles.ringSeg} ${styles.segDown}`}
            d={sectorPath("down")}
            data-jog-action="down"
            role="button"
            tabIndex={0}
            aria-label={`Jog ${SEGMENT_LABELS.down}`}
            aria-pressed={isHeldOnWire(hardwareHeld, "down") || optimistic.down}
            data-pressed={
              isHeldOnWire(hardwareHeld, "down") || optimistic.down ? "true" : undefined
            }
            data-optimistic={
              optimistic.down && !isHeldOnWire(hardwareHeld, "down") ? "true" : undefined
            }
          />
          <path
            className={`${styles.ringSeg} ${styles.segLeft}`}
            d={sectorPath("left")}
            data-jog-action="left"
            role="button"
            tabIndex={0}
            aria-label={`Jog ${SEGMENT_LABELS.left}`}
            aria-pressed={isHeldOnWire(hardwareHeld, "left") || optimistic.left}
            data-pressed={
              isHeldOnWire(hardwareHeld, "left") || optimistic.left ? "true" : undefined
            }
            data-optimistic={
              optimistic.left && !isHeldOnWire(hardwareHeld, "left") ? "true" : undefined
            }
          />
        </svg>
        <button
          type="button"
          className={styles.centerBtn}
          data-jog-action="center"
          aria-label={`Jog ${SEGMENT_LABELS.center}`}
          aria-pressed={isHeldOnWire(hardwareHeld, "center") || optimistic.center}
          data-pressed={
            isHeldOnWire(hardwareHeld, "center") || optimistic.center ? "true" : undefined
          }
          data-optimistic={
            optimistic.center && !isHeldOnWire(hardwareHeld, "center") ? "true" : undefined
          }
        >
          <svg className={styles.powerIcon} viewBox="0 0 24 24" aria-hidden>
            <path
              d="M12 2v10M8 7a6 6 0 1 0 8 0"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}

/** Skip re-render when only the live log updates (same hold props). Important on low-power kiosk browsers. */
export const JogPad = memo(JogPadInner);
