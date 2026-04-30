import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  deleteLiveLog,
  deleteRecording,
  fetchDisplayPower,
  fetchRecordingContent,
  fetchRecordingLibrary,
  fetchRecordingState,
  fetchStatus,
  playRecording,
  postLogEntry,
  recordingDownloadUrl,
  renameRecording,
  startRecording,
  stopRecording,
  stopRecordingPlayback,
  updateRecordingContent,
  uploadRecording,
  websocketEventsUrl,
} from "../api/client";
import { formatBusLedLogMessage } from "../log/busLogFormat";
import type {
  JogAction,
  RecordingLibrary,
  RecordingState,
  SignalSnapshot,
  StatusPayload,
  WsEventV1,
} from "../types";

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

const EMPTY_RECORDING_STATE: RecordingState = {
  mode: "idle",
  recording_started_at: null,
  replay_started_at: null,
  replay_total_duration_ms: null,
  replaying_id: null,
  active_name: null,
  event_count: 0,
  last_error: null,
};

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
  hardwareHeld: Record<JogAction, boolean>;
  wsReleaseTick: number;
  wsReleasedActions: readonly JogAction[];
  wsSessionEpoch: number;
  openPowerMenuTick: number;
  displayOn: boolean;
  logLines: readonly string[];
  recordingState: RecordingState;
  recordings: RecordingLibrary;
  pushLogLine: (line: string) => void;
  clearServerLog: () => Promise<void>;
  refreshStatus: () => Promise<void>;
  refreshRecordings: () => Promise<void>;
  refreshRecordingState: () => Promise<void>;
  startRecording: () => Promise<boolean>;
  stopRecording: () => Promise<boolean>;
  playRecording: (recordingId: string) => Promise<boolean>;
  stopRecordingPlayback: () => Promise<boolean>;
  renameRecording: (recordingId: string, name: string) => Promise<boolean>;
  deleteRecording: (recordingId: string) => Promise<boolean>;
  uploadRecording: (file: File) => Promise<boolean>;
  fetchRecordingContent: (recordingId: string) => Promise<string | null>;
  updateRecordingContent: (recordingId: string, content: string) => Promise<boolean>;
  recordingDownloadUrl: (recordingId: string) => string;
}

function parseWs(raw: string): WsEventV1 | null {
  try {
    const o = JSON.parse(raw) as WsEventV1;
    if (o && o.v === 1 && typeof o.category === "string" && typeof o.type === "string") {
      return o;
    }
  } catch {
    /* ignore */
  }
  return null;
}

function isRecordingState(data: unknown): data is RecordingState {
  if (typeof data !== "object" || data === null) return false;
  const d = data as Record<string, unknown>;
  return d.mode === "idle" || d.mode === "recording" || d.mode === "replaying";
}

function isRecordingLibrary(data: unknown): data is RecordingLibrary {
  if (typeof data !== "object" || data === null) return false;
  const d = data as Record<string, unknown>;
  return Array.isArray(d.items);
}

export function useDeckEvents(): DeckEventsState {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [wsReleaseTick, setWsReleaseTick] = useState(0);
  const [wsReleasedActions, setWsReleasedActions] = useState<readonly JogAction[]>([]);
  const [wsSessionEpoch, setWsSessionEpoch] = useState(0);
  const [openPowerMenuTick, setOpenPowerMenuTick] = useState(0);
  const [displayOn, setDisplayOn] = useState(true);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [recordingState, setRecordingState] = useState<RecordingState>(EMPTY_RECORDING_STATE);
  const [recordings, setRecordings] = useState<RecordingLibrary>({ items: [] });
  const prevSignalsRef = useRef<SignalSnapshot | null>(null);

  const hardwareHeld = useMemo(
    () => (status ? signalsToHardwareHeld(status.signals) : emptyHardwareHeld()),
    [status],
  );

  const pushLogLine = useCallback((line: string) => {
    void postLogEntry({ source: "ui", message: line }).catch(() => {});
  }, []);

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
      setStatus(await fetchStatus());
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      pushLogLine(`status fetch failed — ${msg}`);
    }
  }, [pushLogLine]);

  const refreshRecordings = useCallback(async () => {
    try {
      setRecordings(await fetchRecordingLibrary());
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      pushLogLine(`recordings fetch failed — ${msg}`);
    }
  }, [pushLogLine]);

  const refreshRecordingState = useCallback(async () => {
    try {
      setRecordingState(await fetchRecordingState());
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      pushLogLine(`recording state fetch failed — ${msg}`);
    }
  }, [pushLogLine]);

  const startRecordingAction = useCallback(async () => {
    try {
      const r = await startRecording();
      if (!r.ok) {
        pushLogLine(`recording start rejected — ${r.body.message}`);
        return false;
      }
      setRecordingState(r.body);
      return true;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      pushLogLine(`recording start failed — ${msg}`);
      return false;
    }
  }, [pushLogLine]);

  const stopRecordingAction = useCallback(async () => {
    try {
      const r = await stopRecording();
      if (!r.ok) {
        pushLogLine(`recording stop rejected — ${r.body.message}`);
        return false;
      }
      await refreshRecordings();
      await refreshRecordingState();
      return true;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      pushLogLine(`recording stop failed — ${msg}`);
      return false;
    }
  }, [pushLogLine, refreshRecordingState, refreshRecordings]);

  const playRecordingAction = useCallback(
    async (recordingId: string) => {
      try {
        const r = await playRecording(recordingId);
        if (!r.ok) {
          pushLogLine(`recording play rejected — ${r.body.message}`);
          await refreshRecordingState();
          return false;
        }
        setRecordingState(r.body);
        // Do NOT poll refreshRecordingState here — for fast recordings the WS
        // "idle" event can arrive before a polled HTTP response, and the stale
        // "replaying" HTTP response would then overwrite the correct idle state.
        // The WS broadcast from _run_playback's finally block is the reliable
        // source of truth for the idle transition.
        return true;
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        pushLogLine(`recording play failed — ${msg}`);
        await refreshRecordingState();
        return false;
      }
    },
    [pushLogLine, refreshRecordingState],
  );

  const stopPlaybackAction = useCallback(async () => {
    try {
      const r = await stopRecordingPlayback();
      if (!r.ok) {
        pushLogLine(`recording stop rejected — ${r.body.message}`);
        await refreshRecordingState();
        return false;
      }
      setRecordingState(r.body);
      await refreshRecordingState();
      return true;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      pushLogLine(`recording stop failed — ${msg}`);
      await refreshRecordingState();
      return false;
    }
  }, [pushLogLine, refreshRecordingState]);

  const renameRecordingAction = useCallback(
    async (recordingId: string, name: string) => {
      try {
        const r = await renameRecording(recordingId, name);
        if (!r.ok) {
          pushLogLine(`recording rename rejected — ${r.body.message}`);
          return false;
        }
        await refreshRecordings();
        return true;
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        pushLogLine(`recording rename failed — ${msg}`);
        return false;
      }
    },
    [pushLogLine, refreshRecordings],
  );

  const deleteRecordingAction = useCallback(
    async (recordingId: string) => {
      try {
        const r = await deleteRecording(recordingId);
        if (!r.ok) {
          pushLogLine(`recording delete rejected — ${r.body.message}`);
          return false;
        }
        await refreshRecordings();
        return true;
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        pushLogLine(`recording delete failed — ${msg}`);
        return false;
      }
    },
    [pushLogLine, refreshRecordings],
  );

  const uploadRecordingAction = useCallback(
    async (file: File) => {
      try {
        const r = await uploadRecording(file);
        if (!r.ok) {
          pushLogLine(`recording upload rejected — ${r.body.message}`);
          return false;
        }
        await refreshRecordings();
        return true;
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        pushLogLine(`recording upload failed — ${msg}`);
        return false;
      }
    },
    [pushLogLine, refreshRecordings],
  );

  const fetchRecordingContentAction = useCallback(
    async (recordingId: string) => {
      try {
        return await fetchRecordingContent(recordingId);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        pushLogLine(`recording content fetch failed — ${msg}`);
        return null;
      }
    },
    [pushLogLine],
  );

  const updateRecordingContentAction = useCallback(
    async (recordingId: string, content: string) => {
      try {
        const r = await updateRecordingContent(recordingId, content);
        if (!r.ok) {
          pushLogLine(`recording edit rejected — ${r.body.message}`);
          return false;
        }
        await refreshRecordings();
        return true;
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        pushLogLine(`recording edit failed — ${msg}`);
        return false;
      }
    },
    [pushLogLine, refreshRecordings],
  );

  useEffect(() => {
    void refreshStatus();
    void refreshRecordingState();
    void refreshRecordings();
    fetchDisplayPower().then((p) => setDisplayOn(p.on)).catch(() => {});
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
          fetchDisplayPower().then((p) => setDisplayOn(p.on)).catch(() => {});
        }

        if (parsed.category === "recording" && parsed.type === "state") {
          if (isRecordingState(parsed.data)) {
            setRecordingState(parsed.data);
          }
        }
        if (parsed.category === "recording" && parsed.type === "library") {
          if (isRecordingLibrary(parsed.data)) {
            setRecordings(parsed.data);
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

        if (parsed.category === "display" && parsed.type === "open_power_menu") {
          setOpenPowerMenuTick((n) => n + 1);
        }
        if (parsed.category === "display" && parsed.type === "power_changed") {
          setDisplayOn(Boolean(parsed.data.on));
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
  }, [pushLogLine, refreshRecordingState, refreshRecordings, refreshStatus]);

  return useMemo(
    () => ({
      status,
      hardwareHeld,
      wsReleaseTick,
      wsReleasedActions,
      wsSessionEpoch,
      openPowerMenuTick,
      displayOn,
      logLines,
      recordingState,
      recordings,
      pushLogLine,
      clearServerLog,
      refreshStatus,
      refreshRecordings,
      refreshRecordingState,
      startRecording: startRecordingAction,
      stopRecording: stopRecordingAction,
      playRecording: playRecordingAction,
      stopRecordingPlayback: stopPlaybackAction,
      renameRecording: renameRecordingAction,
      deleteRecording: deleteRecordingAction,
      uploadRecording: uploadRecordingAction,
      fetchRecordingContent: fetchRecordingContentAction,
      updateRecordingContent: updateRecordingContentAction,
      recordingDownloadUrl,
    }),
    [
      status,
      hardwareHeld,
      wsReleaseTick,
      wsReleasedActions,
      wsSessionEpoch,
      openPowerMenuTick,
      displayOn,
      logLines,
      recordingState,
      recordings,
      pushLogLine,
      clearServerLog,
      refreshStatus,
      refreshRecordings,
      refreshRecordingState,
      startRecordingAction,
      stopRecordingAction,
      playRecordingAction,
      stopPlaybackAction,
      renameRecordingAction,
      deleteRecordingAction,
      uploadRecordingAction,
      fetchRecordingContentAction,
      updateRecordingContentAction,
    ],
  );
}
