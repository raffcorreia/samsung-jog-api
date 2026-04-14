import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const { statusPayload } = vi.hoisted(() => ({
  statusPayload: {
    version: "0.0-test",
    hardware: "mock" as const,
    operating_mode: "jog" as const,
    control_state: "idle" as const,
    signals: { key_adc1_active: false, key_led_active: false },
  },
}));

vi.mock("./api/client", () => ({
  fetchStatus: vi.fn(() => Promise.resolve(statusPayload)),
  websocketEventsUrl: vi.fn(() => "ws://localhost/ws/events"),
  jogHold: vi.fn(() => Promise.resolve({ ok: true })),
  releaseJog: vi.fn(() => Promise.resolve({ ok: true, duration_ms: 0 })),
  jogPress: vi.fn(),
}));

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows status from REST and appends websocket command lines to the log", async () => {
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

    expect(await screen.findByText(/v0\.0-test/)).toBeInTheDocument();

    const ws = instances[0];
    expect(ws).toBeDefined();

    await act(async () => {
      ws.onmessage?.({
        data: JSON.stringify({
          v: 1,
          category: "command",
          type: "released",
          ts: "2026-01-01T00:00:00Z",
          data: { action: "up", duration_ms: 80 },
        }),
      } as MessageEvent);
    });

    expect(screen.getByRole("log")).toHaveTextContent("release — up 80ms");
  });
});
