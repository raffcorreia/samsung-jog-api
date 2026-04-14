import {
  useCallback,
  useRef,
  useState,
  type PointerEvent,
} from "react";

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

function mergeHeld(
  local: Record<JogAction, number>,
  peer: Record<JogAction, number>,
  action: JogAction,
): number {
  return Math.max(0, (local[action] ?? 0) + (peer[action] ?? 0));
}

export function JogPad(props: {
  peerHeldActionCounts: Record<JogAction, number>;
  onLocalLog: (line: string) => void;
  restHoldOk: (action: JogAction) => void;
  restReleaseOk: (action: JogAction) => void;
}) {
  const { peerHeldActionCounts, onLocalLog, restHoldOk, restReleaseOk } = props;
  const [localHeldCounts, setLocalHeldCounts] = useState<Record<JogAction, number>>({});
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const ptrMapRef = useRef(new Map<number, PtrState>());

  const bumpLocal = useCallback((action: JogAction, delta: 1 | -1) => {
    setLocalHeldCounts((prev) => {
      const n = Math.max(0, (prev[action] ?? 0) + delta);
      const next: Record<JogAction, number> = { ...prev };
      if (n === 0) {
        delete next[action];
      } else {
        next[action] = n;
      }
      return next;
    });
  }, []);

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
          if (r.ok) {
            bumpLocal(action, -1);
            restReleaseOk(action);
          } else {
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
    [bumpLocal, onLocalLog, restReleaseOk],
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
          bumpLocal(action, 1);
          restHoldOk(action);
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
            aria-pressed={mergeHeld(localHeldCounts, peerHeldActionCounts, "up") > 0}
            data-pressed={mergeHeld(localHeldCounts, peerHeldActionCounts, "up") > 0 ? "true" : undefined}
          />
          <path
            className={`${styles.ringSeg} ${styles.segRight}`}
            d={sectorPath("right")}
            data-jog-action="right"
            role="button"
            tabIndex={0}
            aria-label={`Jog ${SEGMENT_LABELS.right}`}
            aria-pressed={mergeHeld(localHeldCounts, peerHeldActionCounts, "right") > 0}
            data-pressed={mergeHeld(localHeldCounts, peerHeldActionCounts, "right") > 0 ? "true" : undefined}
          />
          <path
            className={`${styles.ringSeg} ${styles.segDown}`}
            d={sectorPath("down")}
            data-jog-action="down"
            role="button"
            tabIndex={0}
            aria-label={`Jog ${SEGMENT_LABELS.down}`}
            aria-pressed={mergeHeld(localHeldCounts, peerHeldActionCounts, "down") > 0}
            data-pressed={mergeHeld(localHeldCounts, peerHeldActionCounts, "down") > 0 ? "true" : undefined}
          />
          <path
            className={`${styles.ringSeg} ${styles.segLeft}`}
            d={sectorPath("left")}
            data-jog-action="left"
            role="button"
            tabIndex={0}
            aria-label={`Jog ${SEGMENT_LABELS.left}`}
            aria-pressed={mergeHeld(localHeldCounts, peerHeldActionCounts, "left") > 0}
            data-pressed={mergeHeld(localHeldCounts, peerHeldActionCounts, "left") > 0 ? "true" : undefined}
          />
        </svg>
        <button
          type="button"
          className={styles.centerBtn}
          data-jog-action="center"
          aria-label={`Jog ${SEGMENT_LABELS.center}`}
          aria-pressed={mergeHeld(localHeldCounts, peerHeldActionCounts, "center") > 0}
          data-pressed={mergeHeld(localHeldCounts, peerHeldActionCounts, "center") > 0 ? "true" : undefined}
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
