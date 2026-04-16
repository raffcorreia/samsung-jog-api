import { describe, expect, it } from "vitest";

import { formatBusLedLogMessage } from "./busLogFormat";

describe("busLogFormat (parity with live_log for LED)", () => {
  it("formats LED line like Python _event_message", () => {
    expect(formatBusLedLogMessage(true)).toBe("key_led -> on");
    expect(formatBusLedLogMessage(false)).toBe("key_led -> off");
  });
});
