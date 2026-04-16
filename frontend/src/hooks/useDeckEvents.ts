import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { deleteLiveLog, fetchStatus, postLogEntry, websocketEventsUrl } from "../api/client";
import { bumpHeldCount } from "./deckHoldPeerSync";
import type { JogAction, SignalSnapshot, StatusPayload, WsEventV1 } from "../types";

const MAX_LOG = 220;

export interface DeckEventsState {
  status: StatusPayload | null;
  /** Hold counts derived only from websocket ``held`` / ``released`` (all clients see the same stream). */
  holdCounts: Record<JogAction, number>;
  /** Increments on each ``released`` so JogPad can drop stale pointer state (replace, peer release). */
  wsReleaseTick: number;
  wsLastReleasedAction: JogAction | null;
  /** Increments on each websocket ``connected`` so JogPad clears stale pointers even when ``wsReleaseTick`` stays 0. */
  wsSessionEpoch: number;
  logLines: readonly string[];
  pushLogLine: (line: string) => void;
  /** Wipes the backend log buffer and clears local lines (DELETE /api/v1/log). */
  clearServerLog: () => Promise<void>;
  refreshStatus: () => Promise<void>;
}

function isJogAction(s: unknown): s is JogAction {
  return (
    s === "up" ||
    s === "down" ||
    s === "left" ||
    s === "right" ||
    s === "center"
  );
}

function parseWs(raw: string): WsEventV1 | null {
  try {
    const o = JSON.parse(raw) as WsEventV1;
    if (o && o.v === 1 && typeof o.category === "string") {
      return o;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function useDeckEvents(): DeckEventsState {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [holdCounts, setHoldCounts] = useState<Record<JogAction, number>>({});
  const [wsReleaseTick, setWsReleaseTick] = useState(0);
  const [wsLastReleasedAction, setWsLastReleasedAction] = useState<JogAction | null>(null);
  const [wsSessionEpoch, setWsSessionEpoch] = useState(0);
  const [logLines, setLogLines] = useState<string[]>([]);
  const prevSignalsRef = useRef<SignalSnapshot | null>(null);

  const pushLogLine = useCallback(
    (line: string) => {
      void postLogEntry({ source: "ui", message: line }).catch(() => {});
    },
    [],
  );

  const clearServerLog = useCallback(async () => {
    try {
      await deleteLiveLog();
      setLogLines([]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      pushLogLine(`log clear failed — ${msg}`);
    }
  }, [pushLogLine]);

  const refreshStatus = useCallback(async () => {
    try {
      const s = await fetchStatus();
      setStatus(s);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      pushLogLine(`status fetch failed — ${msg}`);
    }
  }, [pushLogLine]);

  useEffect(() => {
    void refreshStatus();
    let stopped = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let sock: WebSocket | null = null;

    const connectRef: { fn?: () => void } = {};

    const scheduleReconnect = () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectRef.fn?.();
      }, 1500);
    };

    const connect = () => {
      if (stopped) {
        return;
      }
      const url = websocketEventsUrl();
      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        pushLogLine(`websocket open failed — ${msg}`);
        scheduleReconnect();
        return;
      }
      sock = ws;

      ws.onmessage = (ev) => {
        const parsed = parseWs(String(ev.data));
        if (!parsed) {
          return;
        }

        /* Jog ring + session: sync updates so the UI is not deferred behind startTransition. */
        if (parsed.category === "control" && parsed.type === "connected") {
          const st = parsed.data.status as StatusPayload | undefined;
          if (st) {
            setStatus(st);
            prevSignalsRef.current = st.signals;
          }
          setHoldCounts({});
          setWsReleaseTick(0);
          setWsLastReleasedAction(null);
          setWsSessionEpoch((e) => e + 1);
          setLogLines([]);
        }
        if (parsed.category === "command" && parsed.type === "held") {
          const action = parsed.data.action;
          if (isJogAction(action)) {
            setHoldCounts((prev) => bumpHeldCount(prev, action, 1));
          }
        }
        if (parsed.category === "command" && parsed.type === "released") {
          const action = parsed.data.action;
          if (isJogAction(action)) {
            setHoldCounts((prev) => bumpHeldCount(prev, action, -1));
            setWsLastReleasedAction(action);
            setWsReleaseTick((n) => n + 1);
          }
        }

        if (parsed.category === "log" && parsed.type === "cleared") {
          setLogLines([]);
        }
        if (parsed.category === "log" && parsed.type === "entry") {
          const message = String(parsed.data.message ?? "");
          const source = String(parsed.data.source ?? "log");
          const stamp = parsed.ts.replace("T", " ").replace("Z", "").slice(0, 19);
          const line = `${stamp}  ${source}  ${message}`;
          setLogLines((prev) => {
            const next = [...prev, line];
            return next.length > MAX_LOG ? next.slice(next.length - MAX_LOG) : next;
          });
        }

        /* Status mirrors that are not jog-critical — low priority. */
        if (parsed.category === "control" && parsed.type === "state") {
          startTransition(() => {
            setStatus((prev) =>
              prev
                ? {
                    ...prev,
                    control_state: parsed.data.control_state as StatusPayload["control_state"],
                    operating_mode: parsed.data.operating_mode as StatusPayload["operating_mode"],
                  }
                : prev,
            );
          });
        }
        if (parsed.category === "bus" && parsed.type === "snapshot") {
          const nextSig: SignalSnapshot = {
            key_adc1_active: Boolean(parsed.data.key_adc1_active),
            key_led_active: Boolean(parsed.data.key_led_active),
          };
          prevSignalsRef.current = nextSig;
          startTransition(() => {
            setStatus((p) =>
              p
                ? {
                    ...p,
                    signals: nextSig,
                  }
                : p,
            );
          });
        }
        if (parsed.category === "bus" && parsed.type === "led_changed") {
          const keyLedActive = Boolean(parsed.data.key_led_active);
          prevSignalsRef.current = prevSignalsRef.current
            ? {
                ...prevSignalsRef.current,
                key_led_active: keyLedActive,
              }
            : {
                key_adc1_active: false,
                key_led_active: keyLedActive,
              };
          startTransition(() => {
            setStatus((p) =>
              p
                ? {
                    ...p,
                    signals: {
                      ...p.signals,
                      key_led_active: keyLedActive,
                    },
                  }
                : p,
            );
          });
        }
      };

      ws.onerror = () => {
        pushLogLine("websocket error");
      };

      ws.onclose = () => {
        sock = null;
        if (!stopped) {
          scheduleReconnect();
        }
      };
    };

    connectRef.fn = connect;
    connect();

    return () => {
      stopped = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (sock) {
        sock.close();
        sock = null;
      }
    };
  }, [pushLogLine, refreshStatus]);

  return useMemo(
    () => ({
      status,
      holdCounts,
      wsReleaseTick,
      wsLastReleasedAction,
      wsSessionEpoch,
      logLines,
      pushLogLine,
      clearServerLog,
      refreshStatus,
    }),
    [
      status,
      holdCounts,
      wsReleaseTick,
      wsLastReleasedAction,
      wsSessionEpoch,
      logLines,
      pushLogLine,
      clearServerLog,
      refreshStatus,
    ],
  );
}
