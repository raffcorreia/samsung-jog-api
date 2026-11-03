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
  fetchLedCommunicationStatus: vi.fn(() => Promise.resolve({
    capturing: true,
    level: null,
    accepted_edges: 0,
    rejected_glitches: 0,
    overruns: 0,
    buffered_edges: 0,
    buffer_size: 4096,
    glitch_ns: 250000,
    half_bit_ns: 10000000,
    tolerance: 0.35,
    intervals: { min_ns: null, median_ns: null, max_ns: null },
    valid_frames: 0,
    missing_frames: 0,
    decoder_rejections: 0,
    latest_frame: null,
  })),
  startLedCommunication: vi.fn(),
  stopLedCommunication: vi.fn(),
  clearLedCommunication: vi.fn(),
  replayLedCommunication: vi.fn(),
  ledCommunicationExportUrl: vi.fn(() => "/api/v1/led-communication/export"),
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
    expect(screen.getByTestId("led-communication-monitor")).toBeInTheDocument();
    expect(screen.queryByText("April 2026")).not.toBeInTheDocument();

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

    await act(async () => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          category: "led_comm",
          type: "edge_batch",
          ts: "2026-01-01T00:00:01Z",
          data: {
            edges: [
              { seq: 1, monotonic_ns: 1_000_000_000, level: 0, interval_ns: null },
              { seq: 2, monotonic_ns: 1_010_000_000, level: 1, interval_ns: 10_000_000 },
            ],
            frames: [],
            status: {
              capturing: true,
              level: 1,
              accepted_edges: 2,
              rejected_glitches: 0,
              overruns: 0,
              buffered_edges: 2,
              buffer_size: 4096,
              glitch_ns: 250000,
              half_bit_ns: 10000000,
              tolerance: 0.35,
              intervals: { min_ns: 10000000, median_ns: 10000000, max_ns: 10000000 },
              valid_frames: 1,
              missing_frames: 0,
              decoder_rejections: 0,
              latest_frame: {
                edge_seq: 2,
                monotonic_ns: 1_000_000_000,
                raw_hex: "ffff2dd41100232000",
                sequence: 0,
                layout: "pbp",
                input1: "tb",
                input2: "dp",
                crc: 0,
              },
            },
          },
        }),
      } as MessageEvent);
    });

    expect(screen.getAllByText(/#0 · PBP · TB \/ DP/).length).toBeGreaterThan(0);

    await act(async () => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          category: "led_comm",
          type: "frame",
          ts: "2026-01-01T00:00:02Z",
          data: {
            edge_seq: 120,
            monotonic_ns: 2_000_000_000,
            raw_hex: "ffff2dd4120102309a",
            sequence: 1,
            crc: 0x9a,
            message_type: "level",
            type_code: 0x12,
            level: 2,
            raw_value: 0x30,
          },
        }),
      } as MessageEvent);
    });

    expect(screen.getByText("LEVEL #1 · band 2 connected · raw 0x30 (48)")).toBeInTheDocument();
    expect(screen.getByText(/Latest STATE: #0 · PBP · TB \/ DP/)).toBeInTheDocument();
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
