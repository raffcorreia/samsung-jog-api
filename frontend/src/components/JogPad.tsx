import { memo, useCallback, useEffect, useRef, useState, type PointerEvent } from "react";

import { jogHold, releaseJog } from "../api/client";
import type { JogAction } from "../types";

import { annulusSectorPath } from "./jogGeometry";

import styles from "./JogPad.module.css";

/** Minimum time a sector looks pressed (UI-only; drive timing unchanged). */
const MIN_PRESSED_VISUAL_MS = 160;

const JOG_ACTIONS: readonly JogAction[] = ["up", "down", "left", "right", "center"];

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

function emptyVisual(): Record<JogAction, boolean> {
  return emptyOptimistic();
}

function JogPadInner(props: {
  hardwareHeld: Record<JogAction, boolean>;
  wsReleaseTick: number;
  wsReleasedActions: readonly JogAction[];
  wsSessionEpoch: number;
  onLocalLog: (line: string) => void;
}) {
  const { hardwareHeld, wsReleaseTick, wsReleasedActions, wsSessionEpoch, onLocalLog } = props;
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const ptrMapRef = useRef(new Map<number, PtrState>());
  const [optimistic, setOptimistic] = useState(() => emptyOptimistic());
  /**
   * Pointer-only highlight (not merged into wire ``truth``) so REST + ``bus/snapshot`` stay aligned
   * with ``hardwareHeld`` / optimistic; still shows a flash on slow clients before hold ACK.
   */
  const [pointerGlow, setPointerGlow] = useState(() => emptyOptimistic());
  /** Display-only pressed state from wire truth (may lag by up to ``MIN_PRESSED_VISUAL_MS`` on release). */
  const [visualHeld, setVisualHeld] = useState(() => emptyVisual());
  const prevTruthRef = useRef<Record<JogAction, boolean>>(emptyVisual());
  const pressStartMsRef = useRef<Partial<Record<JogAction, number>>>({});
  const hideTimerRef = useRef<Partial<Record<JogAction, ReturnType<typeof setTimeout>>>>({});
  const pointerGlowStartMsRef = useRef<Partial<Record<JogAction, number>>>({});
  const pointerGlowHideTimerRef = useRef<Partial<Record<JogAction, ReturnType<typeof setTimeout>>>>({});
  const latestTruthRef = useRef<Record<JogAction, boolean>>(emptyVisual());
  const sessionEpochSeenRef = useRef(wsSessionEpoch);

  for (const a of JOG_ACTIONS) {
    latestTruthRef.current[a] = Boolean(hardwareHeld[a]) || Boolean(optimistic[a]);
  }

  const clearHideTimer = useCallback((a: JogAction) => {
    const t = hideTimerRef.current[a];
    if (t !== undefined) {
      clearTimeout(t);
      delete hideTimerRef.current[a];
    }
  }, []);

  const clearPointerGlowHideTimer = useCallback((a: JogAction) => {
    const t = pointerGlowHideTimerRef.current[a];
    if (t !== undefined) {
      clearTimeout(t);
      delete pointerGlowHideTimerRef.current[a];
    }
  }, []);

  /* Truth edges + minimum visible press duration (display only). On websocket reconnect, snap
   * visual state to wire (no artificial delay) so nothing stays stuck. */
  useEffect(() => {
    const epochChanged = sessionEpochSeenRef.current !== wsSessionEpoch;
    sessionEpochSeenRef.current = wsSessionEpoch;

    if (epochChanged) {
      for (const rec of ptrMapRef.current.values()) {
        rec.holdEstablished = false;
      }
      setOptimistic(emptyOptimistic());
      setPointerGlow(emptyOptimistic());
      for (const a of JOG_ACTIONS) {
        clearHideTimer(a);
        clearPointerGlowHideTimer(a);
        delete pointerGlowStartMsRef.current[a];
      }
      const snap = emptyVisual();
      for (const a of JOG_ACTIONS) {
        const w = Boolean(hardwareHeld[a]);
        snap[a] = w;
        prevTruthRef.current[a] = w;
        if (w) {
          pressStartMsRef.current[a] = performance.now();
        } else {
          delete pressStartMsRef.current[a];
        }
      }
      setVisualHeld(snap);
      return;
    }

    for (const a of JOG_ACTIONS) {
      const truth = Boolean(hardwareHeld[a]) || Boolean(optimistic[a]);
      const prev = prevTruthRef.current[a];
      if (truth === prev) {
        continue;
      }
      if (truth && !prev) {
        clearHideTimer(a);
        pressStartMsRef.current[a] = performance.now();
        setVisualHeld((v) => ({ ...v, [a]: true }));
      } else if (!truth && prev) {
        const start = pressStartMsRef.current[a];
        const elapsed =
          start !== undefined ? performance.now() - start : MIN_PRESSED_VISUAL_MS;
        const rem = Math.max(0, MIN_PRESSED_VISUAL_MS - elapsed);
        clearHideTimer(a);
        if (rem <= 0) {
          delete pressStartMsRef.current[a];
          setVisualHeld((v) => ({ ...v, [a]: false }));
        } else {
          hideTimerRef.current[a] = window.setTimeout(() => {
            delete hideTimerRef.current[a];
            if (!latestTruthRef.current[a]) {
              setVisualHeld((v) => ({ ...v, [a]: false }));
            }
            delete pressStartMsRef.current[a];
          }, rem);
        }
      }
      prevTruthRef.current[a] = truth;
    }
  }, [clearHideTimer, clearPointerGlowHideTimer, hardwareHeld, optimistic, wsSessionEpoch]);

  useEffect(() => {
    return () => {
      for (const a of JOG_ACTIONS) {
        const t = hideTimerRef.current[a];
        if (t !== undefined) {
          clearTimeout(t);
        }
        const pt = pointerGlowHideTimerRef.current[a];
        if (pt !== undefined) {
          clearTimeout(pt);
        }
      }
    };
  }, []);

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

  /* Wire released (peer tab, watchdog, or own gesture completing on the bus): clear optimistic
   * overlay and drop local hold bookkeeping so we never show “stuck pressed” after remote idle. */
  useEffect(() => {
    if (wsReleaseTick === 0 || wsReleasedActions.length === 0) {
      return;
    }
    const released = new Set(wsReleasedActions);
    setOptimistic((prev) => {
      let next = prev;
      for (const a of released) {
        if (prev[a]) {
          if (next === prev) {
            next = { ...prev };
          }
          next[a] = false;
        }
      }
      return next;
    });
    for (const rec of ptrMapRef.current.values()) {
      if (released.has(rec.action) && rec.holdEstablished) {
        rec.holdEstablished = false;
      }
    }
  }, [wsReleaseTick, wsReleasedActions]);

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
      const action = rec.action;
      try {
        try {
          await rec.downPromise;
        } catch {
          /* ignore */
        }
        if (!rec.holdEstablished) {
          return;
        }
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
        /* Always clear local optimistic for this gesture so a tab never sticks “pressed”
         * if the wire already idled or REST errored. */
        setOptimistic((o) => ({ ...o, [action]: false }));
        const g0 = pointerGlowStartMsRef.current[action];
        const gElapsed =
          g0 !== undefined ? performance.now() - g0 : MIN_PRESSED_VISUAL_MS;
        const gRem = Math.max(0, MIN_PRESSED_VISUAL_MS - gElapsed);
        clearPointerGlowHideTimer(action);
        if (gRem <= 0) {
          delete pointerGlowStartMsRef.current[action];
          setPointerGlow((o) => ({ ...o, [action]: false }));
        } else {
          pointerGlowHideTimerRef.current[action] = window.setTimeout(() => {
            delete pointerGlowHideTimerRef.current[action];
            delete pointerGlowStartMsRef.current[action];
            setPointerGlow((o) => ({ ...o, [action]: false }));
          }, gRem);
        }
        ptrMapRef.current.delete(pointerId);
        rec.releaseInFlight = false;
      }
    },
    [clearPointerGlowHideTimer, onLocalLog],
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

    clearPointerGlowHideTimer(action);
    pointerGlowStartMsRef.current[action] = performance.now();
    setPointerGlow((o) => ({ ...o, [action]: true }));

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
            aria-pressed={visualHeld.up || pointerGlow.up}
            data-pressed={visualHeld.up || pointerGlow.up ? "true" : undefined}
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
            aria-pressed={visualHeld.right || pointerGlow.right}
            data-pressed={visualHeld.right || pointerGlow.right ? "true" : undefined}
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
            aria-pressed={visualHeld.down || pointerGlow.down}
            data-pressed={visualHeld.down || pointerGlow.down ? "true" : undefined}
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
            aria-pressed={visualHeld.left || pointerGlow.left}
            data-pressed={visualHeld.left || pointerGlow.left ? "true" : undefined}
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
          aria-pressed={visualHeld.center || pointerGlow.center}
          data-pressed={visualHeld.center || pointerGlow.center ? "true" : undefined}
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
