import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useDeckEvents } from "./useDeckEvents";

vi.mock("../api/client", () => ({
  fetchStatus: vi.fn(() =>
    Promise.resolve({
      version: "t",
      hardware: "mock" as const,
      operating_mode: "jog" as const,
      control_state: "idle" as const,
      signals: { key_adc1_active: false, key_led_active: false },
    }),
  ),
  websocketEventsUrl: vi.fn(() => "ws://localhost/ws/events"),
  postLogEntry: vi.fn(() => Promise.resolve()),
}));

describe("useDeckEvents holdCounts (WS-only)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("applies held +1 and released -1 for every client (no local/peer split)", async () => {
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
          category: "command",
          type: "held",
          ts: "2026-01-01T00:00:00Z",
          data: { action: "left" },
        }),
      } as MessageEvent);
    });
    expect(result.current.holdCounts.left).toBe(1);

    await act(async () => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          category: "command",
          type: "released",
          ts: "2026-01-01T00:00:00Z",
          data: { action: "left", duration_ms: 10 },
        }),
      } as MessageEvent);
    });
    expect(result.current.holdCounts.left).toBeUndefined();

    await act(async () => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          category: "command",
          type: "held",
          ts: "2026-01-01T00:00:01Z",
          data: { action: "left" },
        }),
      } as MessageEvent);
    });
    expect(result.current.holdCounts.left).toBe(1);
  });
});
