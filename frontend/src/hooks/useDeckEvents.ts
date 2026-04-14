import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { fetchStatus, websocketEventsUrl } from "../api/client";
import { bumpHeldCount } from "./deckHoldPeerSync";
import { formatWsEventLine } from "../log/formatWsEvent";
import type { JogAction, StatusPayload, WsEventV1 } from "../types";

const MAX_LOG = 220;

export interface DeckEventsState {
  status: StatusPayload | null;
  peerHeldActionCounts: Record<JogAction, number>;
  wsConnected: boolean;
  wsError: string | null;
  logLines: readonly string[];
  pushLogLine: (line: string) => void;
  refreshStatus: () => Promise<void>;
  /** After REST ``jog/hold`` succeeds — skip duplicate peer ``held`` for this action. */
  restHoldOk: (action: JogAction) => void;
  /** After REST ``jog/release`` succeeds — skip echo ``released`` for this action. */
  restReleaseOk: (action: JogAction) => void;
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
  const [peerHeldActionCounts, setPeerHeldActionCounts] = useState<Record<JogAction, number>>({});
  const [wsConnected, setWsConnected] = useState(false);
  const [wsError, setWsError] = useState<string | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const sockRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stopped = useRef(false);

  /** Directions we established via REST hold in this browser (skip duplicate WS ``held``). */
  const myLocalHeldRef = useRef(new Set<JogAction>());
  /** Skip next ``released`` WS — our REST release already updated local state. */
  const skipReleasedEchoRef = useRef(new Set<JogAction>());

  const restHoldOk = useCallback((action: JogAction) => {
    myLocalHeldRef.current.add(action);
    /* Undo the peer +1 from our own ``held`` websocket echo so local+peer does not double-count. */
    setPeerHeldActionCounts((prev) => bumpHeldCount(prev, action, -1));
  }, []);

  const restReleaseOk = useCallback((action: JogAction) => {
    myLocalHeldRef.current.delete(action);
    skipReleasedEchoRef.current.add(action);
  }, []);

  const pushLogLine = useCallback((line: string) => {
    const stamp = new Date().toISOString().replace("T", " ").slice(0, 19);
    setLogLines((prev) => {
      const next = [...prev, `${stamp}  ${line}`];
      if (next.length > MAX_LOG) {
        return next.slice(next.length - MAX_LOG);
      }
      return next;
    });
  }, []);

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
    stopped.current = false;
    void refreshStatus();

    const connectRef: { fn?: () => void } = {};

    const scheduleReconnect = () => {
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      reconnectTimer.current = setTimeout(() => {
        reconnectTimer.current = null;
        connectRef.fn?.();
      }, 1500);
    };

    const connect = () => {
      if (stopped.current) {
        return;
      }
      setWsError(null);
      const url = websocketEventsUrl();
      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setWsError(msg);
        pushLogLine(`websocket open failed — ${msg}`);
        scheduleReconnect();
        return;
      }
      sockRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (ev) => {
        const parsed = parseWs(String(ev.data));
        if (!parsed) {
          return;
        }
        startTransition(() => {
          pushLogLine(formatWsEventLine(parsed));
          if (parsed.category === "control" && parsed.type === "connected") {
            const st = parsed.data.status as StatusPayload | undefined;
            if (st) {
              setStatus(st);
            }
            setPeerHeldActionCounts({});
            myLocalHeldRef.current.clear();
            skipReleasedEchoRef.current.clear();
          }
          if (parsed.category === "command" && parsed.type === "held") {
            const action = parsed.data.action;
            if (!isJogAction(action)) {
              return;
            }
            if (myLocalHeldRef.current.has(action)) {
              return;
            }
            setPeerHeldActionCounts((prev) => bumpHeldCount(prev, action, 1));
          }
          if (parsed.category === "command" && parsed.type === "released") {
            const action = parsed.data.action;
            if (!isJogAction(action)) {
              return;
            }
            if (skipReleasedEchoRef.current.has(action)) {
              skipReleasedEchoRef.current.delete(action);
              return;
            }
            setPeerHeldActionCounts((prev) => bumpHeldCount(prev, action, -1));
          }
          if (parsed.category === "control" && parsed.type === "state") {
            setStatus((prev) =>
              prev
                ? {
                    ...prev,
                    control_state: parsed.data.control_state as StatusPayload["control_state"],
                    operating_mode: parsed.data.operating_mode as StatusPayload["operating_mode"],
                  }
                : prev,
            );
          }
          if (parsed.category === "bus" && parsed.type === "snapshot") {
            setStatus((prev) =>
              prev
                ? {
                    ...prev,
                    signals: {
                      key_adc1_active: Boolean(parsed.data.key_adc1_active),
                      key_led_active: Boolean(parsed.data.key_led_active),
                    },
                  }
                : prev,
            );
          }
        });
      };

      ws.onerror = () => {
        setWsError("websocket error");
      };

      ws.onclose = () => {
        setWsConnected(false);
        sockRef.current = null;
        if (!stopped.current) {
          scheduleReconnect();
        }
      };
    };

    connectRef.fn = connect;
    connect();

    return () => {
      stopped.current = true;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      if (sockRef.current) {
        sockRef.current.close();
        sockRef.current = null;
      }
    };
  }, [pushLogLine, refreshStatus]);

  return useMemo(
    () => ({
      status,
      peerHeldActionCounts,
      wsConnected,
      wsError,
      logLines,
      pushLogLine,
      refreshStatus,
      restHoldOk,
      restReleaseOk,
    }),
    [
      status,
      peerHeldActionCounts,
      wsConnected,
      wsError,
      logLines,
      pushLogLine,
      refreshStatus,
      restHoldOk,
      restReleaseOk,
    ],
  );
}
