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
  /** Holds from other viewers / race-ahead WS (not deduped against local REST here). */
  peerHeldActionCounts: Record<JogAction, number>;
  wsConnected: boolean;
  wsError: string | null;
  logLines: readonly string[];
  pushLogLine: (line: string) => void;
  refreshStatus: () => Promise<void>;
  /** Call after REST ``jog/down`` succeeds — pairs tokens with this UI for WS dedup. */
  restHoldDownOk: (token: string, action: JogAction) => void;
  /** Call after REST ``jog/up`` succeeds — updates local REST mirror (see JogPad). */
  restHoldUpOk: (token: string) => void;
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

  /** REST-issued tokens for *this* browser — skip matching WS hold_started so we don't double-count with JogPad local REST refcounts. */
  const myHoldTokensRef = useRef(new Set<string>());
  /**
   * If ``hold_started`` arrives before REST returns, we bump peer once; when REST later
   * confirms, we undo that bump (same token).
   */
  const peerPreRestTokensRef = useRef(new Map<string, JogAction>());

  const restHoldDownOk = useCallback((token: string, action: JogAction) => {
    myHoldTokensRef.current.add(token);
    const pre = peerPreRestTokensRef.current.get(token);
    if (pre !== undefined) {
      peerPreRestTokensRef.current.delete(token);
      if (pre === action) {
        setPeerHeldActionCounts((prev) => bumpHeldCount(prev, action, -1));
      }
    }
  }, []);

  const restHoldUpOk = useCallback((token: string) => {
    myHoldTokensRef.current.delete(token);
  }, []);

  /** Append one line; keep synchronous for local tap feedback (Pi / kiosk). */
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
        /* Defer server-driven log + status so Pi Chromium can paint local taps first. */
        startTransition(() => {
          pushLogLine(formatWsEventLine(parsed));
          if (parsed.category === "control" && parsed.type === "connected") {
            const st = parsed.data.status as StatusPayload | undefined;
            if (st) {
              setStatus(st);
            }
            setPeerHeldActionCounts({});
            peerPreRestTokensRef.current.clear();
            /* Keep myHoldTokensRef — REST-issued tokens still valid; only peer mirror resets. */
          }
          if (parsed.category === "command" && parsed.type === "hold_started") {
            const token = String(parsed.data.hold_token ?? "");
            const action = parsed.data.action;
            if (!token || !isJogAction(action)) {
              return;
            }
            if (myHoldTokensRef.current.has(token)) {
              return;
            }
            peerPreRestTokensRef.current.set(token, action);
            setPeerHeldActionCounts((prev) => bumpHeldCount(prev, action, 1));
          }
          if (parsed.category === "command" && parsed.type === "accepted") {
            const holdToken = parsed.data.hold_token;
            if (holdToken === "pulse") {
              /* timed pulse — not a directional hold */
            } else {
              const token = String(holdToken ?? "");
              const action = parsed.data.action;
              if (!token || !isJogAction(action)) {
                return;
              }
              peerPreRestTokensRef.current.delete(token);
              if (myHoldTokensRef.current.has(token)) {
                return;
              }
              setPeerHeldActionCounts((prev) => bumpHeldCount(prev, action, -1));
            }
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
      restHoldDownOk,
      restHoldUpOk,
    }),
    [
      status,
      peerHeldActionCounts,
      wsConnected,
      wsError,
      logLines,
      pushLogLine,
      refreshStatus,
      restHoldDownOk,
      restHoldUpOk,
    ],
  );
}
