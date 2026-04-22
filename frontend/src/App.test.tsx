import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const { statusPayload } = vi.hoisted(() => ({
  statusPayload: {
    version: "0.0-test",
    hardware: "mock" as const,
    operating_mode: "jog" as const,
    control_state: "idle" as const,
    signals: {
      key_adc1_active: false,
      key_led_active: false,
      key_adc2_direction: null,
    },
  },
}));

vi.mock("./api/client", () => ({
  fetchStatus: vi.fn(() => Promise.resolve(statusPayload)),
  fetchRecordingLibrary: vi.fn(() => Promise.resolve({ items: [] })),
  fetchRecordingState: vi.fn(() =>
    Promise.resolve({
      mode: "idle",
      recording_started_at: null,
      replaying_id: null,
      active_name: null,
      event_count: 0,
      last_error: null,
    }),
  ),
  websocketEventsUrl: vi.fn(() => "ws://localhost/ws/events"),
  postLogEntry: vi.fn(() => Promise.resolve()),
  deleteLiveLog: vi.fn(() => Promise.resolve()),
  startRecording: vi.fn(),
  stopRecording: vi.fn(),
  playRecording: vi.fn(),
  stopRecordingPlayback: vi.fn(),
  renameRecording: vi.fn(),
  deleteRecording: vi.fn(),
  uploadRecording: vi.fn(),
  fetchRecordingContent: vi.fn(),
  updateRecordingContent: vi.fn(),
  recordingDownloadUrl: vi.fn((id: string) => `/api/v1/recordings/${id}/download`),
  jogHold: vi.fn(() => Promise.resolve({ ok: true })),
  releaseJog: vi.fn(() => Promise.resolve({ ok: true, duration_ms: 0 })),
  jogPress: vi.fn(),
  fetchDisplayPower: vi.fn(() => Promise.resolve({ on: true, brightness_pct: 30 })),
  setDisplayPower: vi.fn(() => Promise.resolve({ on: true, brightness_pct: 30 })),
  fetchDisplayBrightness: vi.fn(() =>
    Promise.resolve({ brightness_pct: 30, brightness_raw: 51, max_raw: 170 }),
  ),
  setDisplayBrightness: vi.fn(() =>
    Promise.resolve({ brightness_pct: 30, brightness_raw: 51, max_raw: 170 }),
  ),
  requestShutdown: vi.fn(() => Promise.resolve({ ok: true, message: "Shutdown initiated" })),
}));

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows status from REST and renders backend log entries", async () => {
    const instances: { onmessage: ((ev: MessageEvent) => void) | null }[] = [];

    class MockSocket {
      static OPEN = 1;
      onopen: (() => void) | null = null;
      onmessage: ((ev: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;
      onclose: (() => void) | null = null;
      constructor(_url: string) {
        instances.push(this);
        queueMicrotask(() => this.onopen?.());
      }
      send() {}
      close() {}
    }

    vi.stubGlobal("WebSocket", MockSocket as unknown as typeof WebSocket);

    render(<App />);

    expect(await screen.findByTestId("jog-pad")).toBeInTheDocument();

    const ws = instances[0];
    expect(ws).toBeDefined();

    await act(async () => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          category: "log",
          type: "entry",
          ts: "2026-01-01T00:00:00Z",
          data: { level: "info", source: "command", message: "release - up 80ms" },
        }),
      } as MessageEvent);
    });

    await waitFor(() => {
      expect(screen.getByRole("log")).toHaveTextContent("release - up 80ms");
    });
  });

  it("opens the recording workspace from the jog column button", async () => {
    const user = userEvent.setup();
    const instances: { onmessage: ((ev: MessageEvent) => void) | null }[] = [];

    class MockSocket {
      static OPEN = 1;
      onopen: (() => void) | null = null;
      onmessage: ((ev: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;
      onclose: (() => void) | null = null;
      constructor(_url: string) {
        instances.push(this);
        queueMicrotask(() => this.onopen?.());
      }
      send() {}
      close() {}
    }

    vi.stubGlobal("WebSocket", MockSocket as unknown as typeof WebSocket);

    render(<App />);

    await screen.findByTestId("jog-pad");

    await user.click(screen.getByRole("button", { name: /open recording workspace/i }));

    expect(await screen.findByText("Library")).toBeInTheDocument();
  });
});
