import { describe, expect, it, vi } from "vitest";

import { jogPress } from "./client";

describe("jogPress", () => {
  it("returns ok on 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({}),
        } as Response),
      ),
    );
    const r = await jogPress("center", 50);
    expect(r.ok).toBe(true);
    vi.unstubAllGlobals();
  });

  it("returns rejection body on 409", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Promise.resolve({
          ok: false,
          status: 409,
          json: async () => ({
            error: "command_rejected",
            reason: "concurrent_command",
            message: "busy",
          }),
        } as Response),
      ),
    );
    const r = await jogPress("up", 10);
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.body.reason).toBe("concurrent_command");
    }
    vi.unstubAllGlobals();
  });
});
