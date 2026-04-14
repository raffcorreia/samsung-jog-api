import {
  useCallback,
  useRef,
  useState,
  type PointerEvent,
} from "react";

import { jogDown, jogUp } from "../api/client";
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
  holdToken: string | null;
  /** True after jog/down returned ok and the segment refcount was incremented. */
  holdEstablished: boolean;
  downPromise: Promise<void>;
  releaseInFlight: boolean;
};

export function JogPad(props: {
  deckBusy: boolean;
  onLocalLog: (line: string) => void;
}) {
  const { deckBusy, onLocalLog } = props;
  const [actionCounts, setActionCounts] = useState<Record<JogAction, number>>({});
  const [localPointerCount, setLocalPointerCount] = useState(0);
  const localPointerCountRef = useRef(0);
  const surfaceRef = useRef<HTMLDivElement | null>(null);
  const ptrMapRef = useRef(new Map<number, PtrState>());

  const bumpAction = useCallback((action: JogAction, delta: 1 | -1) => {
    setActionCounts((prev) => {
      const n = Math.max(0, (prev[action] ?? 0) + delta);
      return { ...prev, [action]: n };
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
        if (!rec.holdEstablished || !rec.holdToken) {
          return;
        }
        const token = rec.holdToken;
        try {
          const r = await jogUp(token);
          bumpAction(rec.action, -1);
          if (!r.ok) {
            onLocalLog(`http jog/up — ${r.body.reason}: ${r.body.message}`);
          }
        } catch (e) {
          bumpAction(rec.action, -1);
          const msg = e instanceof Error ? e.message : String(e);
          onLocalLog(`jog up failed — ${msg}`);
        }
      } finally {
        ptrMapRef.current.delete(pointerId);
        localPointerCountRef.current = Math.max(0, localPointerCountRef.current - 1);
        setLocalPointerCount(localPointerCountRef.current);
        rec.releaseInFlight = false;
      }
    },
    [bumpAction, onLocalLog],
  );

  const onSurfacePointerDown = (ev: PointerEvent<HTMLDivElement>) => {
    if (ev.button !== 0 && ev.button !== -1) {
      return;
    }
    const action = readJogAction(ev);
    if (!action) {
      return;
    }
    if (deckBusy && localPointerCountRef.current === 0) {
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
      holdToken: null,
      holdEstablished: false,
      downPromise,
      releaseInFlight: false,
    };
    ptrMapRef.current.set(ev.pointerId, rec);
    localPointerCountRef.current += 1;
    setLocalPointerCount(localPointerCountRef.current);

    void jogDown(action)
      .then((r) => {
        if (r.ok) {
          rec.holdToken = r.hold_token;
          rec.holdEstablished = true;
          bumpAction(action, 1);
        } else {
          onLocalLog(`http jog/down — ${r.body.reason}: ${r.body.message}`);
        }
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : String(e);
        onLocalLog(`jog down failed — ${msg}`);
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

  const padLocked = deckBusy && localPointerCount === 0;

  return (
    <div className={styles.shell} data-testid="jog-pad" data-touch-policy="none">
      <div
        ref={surfaceRef}
        className={styles.surface}
        data-pad-locked={padLocked ? "true" : undefined}
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
            tabIndex={padLocked ? -1 : 0}
            aria-label={`Jog ${SEGMENT_LABELS.up}`}
            aria-pressed={(actionCounts.up ?? 0) > 0}
            data-pressed={(actionCounts.up ?? 0) > 0 ? "true" : undefined}
          />
          <path
            className={`${styles.ringSeg} ${styles.segRight}`}
            d={sectorPath("right")}
            data-jog-action="right"
            role="button"
            tabIndex={padLocked ? -1 : 0}
            aria-label={`Jog ${SEGMENT_LABELS.right}`}
            aria-pressed={(actionCounts.right ?? 0) > 0}
            data-pressed={(actionCounts.right ?? 0) > 0 ? "true" : undefined}
          />
          <path
            className={`${styles.ringSeg} ${styles.segDown}`}
            d={sectorPath("down")}
            data-jog-action="down"
            role="button"
            tabIndex={padLocked ? -1 : 0}
            aria-label={`Jog ${SEGMENT_LABELS.down}`}
            aria-pressed={(actionCounts.down ?? 0) > 0}
            data-pressed={(actionCounts.down ?? 0) > 0 ? "true" : undefined}
          />
          <path
            className={`${styles.ringSeg} ${styles.segLeft}`}
            d={sectorPath("left")}
            data-jog-action="left"
            role="button"
            tabIndex={padLocked ? -1 : 0}
            aria-label={`Jog ${SEGMENT_LABELS.left}`}
            aria-pressed={(actionCounts.left ?? 0) > 0}
            data-pressed={(actionCounts.left ?? 0) > 0 ? "true" : undefined}
          />
        </svg>
        <button
          type="button"
          className={styles.centerBtn}
          disabled={padLocked}
          data-jog-action="center"
          aria-label={`Jog ${SEGMENT_LABELS.center}`}
          aria-pressed={(actionCounts.center ?? 0) > 0}
          data-pressed={(actionCounts.center ?? 0) > 0 ? "true" : undefined}
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
