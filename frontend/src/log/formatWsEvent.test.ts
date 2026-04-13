import { describe, expect, it } from "vitest";

import { formatWsEventLine } from "./formatWsEvent";
import type { WsEventV1 } from "../types";

describe("formatWsEventLine", () => {
  it("formats connected", () => {
    const ev: WsEventV1 = {
      v: 1,
      category: "control",
      type: "connected",
      ts: "2026-01-01T00:00:00Z",
      data: {
        status: { hardware: "mock", control_state: "idle" },
      },
    };
    expect(formatWsEventLine(ev)).toContain("hardware=mock");
  });

  it("formats command accepted", () => {
    const ev: WsEventV1 = {
      v: 1,
      category: "command",
      type: "accepted",
      ts: "2026-01-01T00:00:00Z",
      data: { action: "up", duration_ms: 120 },
    };
    expect(formatWsEventLine(ev)).toBe("command ok — up 120ms");
  });

  it("formats command rejected", () => {
    const ev: WsEventV1 = {
      v: 1,
      category: "command",
      type: "rejected",
      ts: "2026-01-01T00:00:00Z",
      data: { reason: "bus_busy", message: "nope" },
    };
    expect(formatWsEventLine(ev)).toContain("bus_busy");
    expect(formatWsEventLine(ev)).toContain("nope");
  });
});
