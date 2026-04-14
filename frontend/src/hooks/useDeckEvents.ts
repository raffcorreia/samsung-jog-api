import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { fetchStatus, websocketEventsUrl } from "../api/client";
import { formatWsEventLine } from "../log/formatWsEvent";
import type { StatusPayload, WsEventV1 } from "../types";

const MAX_LOG = 220;

export interface DeckEventsState {
  status: StatusPayload | null;
  wsConnected: boolean;
  wsError: string | null;
  logLines: readonly string[];
  pushLogLine: (line: string) => void;
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
  const [wsConnected, setWsConnected] = useState(false);
  const [wsError, setWsError] = useState<string | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const sockRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stopped = useRef(false);

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
      wsConnected,
      wsError,
      logLines,
      pushLogLine,
      refreshStatus,
    }),
    [status, wsConnected, wsError, logLines, pushLogLine, refreshStatus],
  );
}
