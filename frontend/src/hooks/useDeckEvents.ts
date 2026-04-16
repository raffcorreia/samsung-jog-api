import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { deleteLiveLog, fetchStatus, postLogEntry, websocketEventsUrl } from "../api/client";
import { formatBusLedLogMessage } from "../log/busLogFormat";
import type { JogAction, SignalSnapshot, StatusPayload, WsEventV1 } from "../types";

const MAX_LOG = 220;

const JOG_ACTIONS: readonly JogAction[] = ["up", "down", "left", "right", "center"];

function emptyHardwareHeld(): Record<JogAction, boolean> {
  return {
    up: false,
    down: false,
    left: false,
    right: false,
    center: false,
  };
}

export function signalsToHardwareHeld(s: SignalSnapshot): Record<JogAction, boolean> {
  const h = emptyHardwareHeld();
  if (s.key_adc1_active) {
    h.center = true;
  }
  const d = s.key_adc2_direction;
  if (d === "up" || d === "down" || d === "left" || d === "right") {
    h[d] = true;
  }
  return h;
}

function parseBusSnapshotData(data: Record<string, unknown>): SignalSnapshot {
  const d = data.key_adc2_direction;
  return {
    key_adc1_active: Boolean(data.key_adc1_active),
    key_led_active: Boolean(data.key_led_active),
    key_adc2_direction:
      d === "up" || d === "down" || d === "left" || d === "right" ? d : null,
  };
}

export interface DeckEventsState {
  status: StatusPayload | null;
  /** Observed jog actuation from ``bus/snapshot`` / ``status.signals`` (hardware truth). */
  hardwareHeld: Record<JogAction, boolean>;
  /** Increments when observation shows key(s) no longer held (peer sync / watchdog). */
  wsReleaseTick: number;
  /** Actions that transitioned held→idle on the wire for this tick (may be multiple). */
  wsReleasedActions: readonly JogAction[];
  /** Increments on each websocket ``connected`` so JogPad clears stale pointers. */
  wsSessionEpoch: number;
  logLines: readonly string[];
  pushLogLine: (line: string) => void;
  clearServerLog: () => Promise<void>;
  refreshStatus: () => Promise<void>;
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
  const [wsReleaseTick, setWsReleaseTick] = useState(0);
  const [wsReleasedActions, setWsReleasedActions] = useState<readonly JogAction[]>([]);
  const [wsSessionEpoch, setWsSessionEpoch] = useState(0);
  const [logLines, setLogLines] = useState<string[]>([]);
  const prevSignalsRef = useRef<SignalSnapshot | null>(null);

  const hardwareHeld = useMemo(
    () => (status ? signalsToHardwareHeld(status.signals) : emptyHardwareHeld()),
    [status],
  );

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

        if (parsed.category === "control" && parsed.type === "connected") {
          const st = parsed.data.status as StatusPayload | undefined;
          if (st) {
            setStatus(st);
            prevSignalsRef.current = st.signals;
          }
          setWsReleaseTick(0);
          setWsReleasedActions([]);
          setWsSessionEpoch((e) => e + 1);
          setLogLines([]);
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
          const nextSig = parseBusSnapshotData(parsed.data as Record<string, unknown>);
          const prev = prevSignalsRef.current;
          if (prev) {
            const pHeld = signalsToHardwareHeld(prev);
            const nHeld = signalsToHardwareHeld(nextSig);
            const released: JogAction[] = [];
            for (const a of JOG_ACTIONS) {
              if (pHeld[a] && !nHeld[a]) {
                released.push(a);
              }
            }
            if (released.length > 0) {
              setWsReleasedActions(released);
              setWsReleaseTick((n) => n + 1);
            }
          }
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
          const stamp = parsed.ts.replace("T", " ").replace("Z", "").slice(0, 19);
          const line = `${stamp}  bus  ${formatBusLedLogMessage(keyLedActive)}`;
          setLogLines((prev) => {
            const next = [...prev, line];
            return next.length > MAX_LOG ? next.slice(next.length - MAX_LOG) : next;
          });
          prevSignalsRef.current = prevSignalsRef.current
            ? {
                ...prevSignalsRef.current,
                key_led_active: keyLedActive,
              }
            : {
                key_adc1_active: false,
                key_led_active: keyLedActive,
                key_adc2_direction: null,
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
      hardwareHeld,
      wsReleaseTick,
      wsReleasedActions,
      wsSessionEpoch,
      logLines,
      pushLogLine,
      clearServerLog,
      refreshStatus,
    }),
    [
      status,
      hardwareHeld,
      wsReleaseTick,
      wsReleasedActions,
      wsSessionEpoch,
      logLines,
      pushLogLine,
      clearServerLog,
      refreshStatus,
    ],
  );
}
