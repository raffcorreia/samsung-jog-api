import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { signalsToHardwareHeld, useDeckEvents } from "./useDeckEvents";

vi.mock("../api/client", () => ({
  fetchStatus: vi.fn(() =>
    Promise.resolve({
      version: "t",
      hardware: "mock" as const,
      operating_mode: "jog" as const,
      control_state: "idle" as const,
      signals: {
        key_adc1_active: false,
        key_led_active: false,
        key_adc2_direction: null,
      },
    }),
  ),
  fetchRecordingLibrary: vi.fn(() => Promise.resolve({ items: [] })),
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
  fetchDisplayPower: vi.fn(() => Promise.resolve({ on: true, brightness_pct: 30 })),
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
}));

describe("useDeckEvents hardwareHeld (bus/snapshot)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("derives direction holds from bus/snapshot only", async () => {
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

    const { result } = renderHook(() => useDeckEvents());

    await act(async () => {
      await Promise.resolve();
    });

    const ws = instances[0];
    expect(ws).toBeDefined();

    await act(async () => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          category: "bus",
          type: "snapshot",
          ts: "2026-01-01T00:00:00Z",
          data: {
            key_adc1_active: false,
            key_led_active: false,
            key_adc2_direction: "left",
          },
        }),
      } as MessageEvent);
    });
    expect(result.current.hardwareHeld.left).toBe(true);

    await act(async () => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          category: "bus",
          type: "snapshot",
          ts: "2026-01-01T00:00:01Z",
          data: {
            key_adc1_active: false,
            key_led_active: false,
            key_adc2_direction: null,
          },
        }),
      } as MessageEvent);
    });
    expect(result.current.hardwareHeld.left).toBe(false);
  });
});

describe("signalsToHardwareHeld", () => {
  it("maps center to key_adc1 and one direction from KEY_ADC2", () => {
    const h = signalsToHardwareHeld({
      key_adc1_active: true,
      key_led_active: false,
      key_adc2_direction: "up",
    });
    expect(h.center).toBe(true);
    expect(h.up).toBe(true);
  });
});
