import { describe, expect, it } from "vitest";

import { formatBusLedLogMessage, formatBusSnapshotLogMessage } from "./busLogFormat";

describe("busLogFormat (parity with live_log._bus_snapshot_log_message)", () => {
  it("formats snapshot like Python", () => {
    expect(
      formatBusSnapshotLogMessage({
        key_adc1_active: false,
        key_led_active: true,
        key_adc2_direction: "left",
      }),
    ).toBe(
      "key_adc1_active=false key_adc2_direction=left key_led_active=true",
    );
    expect(
      formatBusSnapshotLogMessage({
        key_adc1_active: true,
        key_led_active: false,
        key_adc2_direction: null,
      }),
    ).toBe("key_adc1_active=true key_adc2_direction=null key_led_active=false");
  });

  it("formats LED line like Python _event_message", () => {
    expect(formatBusLedLogMessage(true)).toBe("key_led -> on");
    expect(formatBusLedLogMessage(false)).toBe("key_led -> off");
  });
});
