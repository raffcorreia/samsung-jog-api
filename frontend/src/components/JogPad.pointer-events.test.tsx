import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../api/client";
import { JogPad } from "./JogPad";

vi.mock("../api/client");

const defaultProps = {
  hardwareHeld: {
    up: false,
    down: false,
    left: false,
    right: false,
    center: false,
  },
  wsReleaseTick: 0,
  wsReleasedActions: [],
  wsSessionEpoch: 0,
  onLocalLog: vi.fn(),
};

function renderPad() {
  render(<JogPad {...defaultProps} />);
}

describe("JogPad pointer events", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(client.jogHold).mockResolvedValue({ ok: true });
    vi.mocked(client.releaseJog).mockResolvedValue({ ok: true, duration_ms: 50 });
  });

  it("calls jogHold when pointer is pressed on a direction", async () => {
    renderPad();
    fireEvent.pointerDown(screen.getByLabelText("Jog Up"), { button: 0, pointerId: 1 });
    await waitFor(() => expect(client.jogHold).toHaveBeenCalledWith("up"));
  });

  it("calls releaseJog on pointer up after hold is established", async () => {
    renderPad();
    const el = screen.getByLabelText("Jog Up");
    fireEvent.pointerDown(el, { button: 0, pointerId: 1 });
    await waitFor(() => expect(client.jogHold).toHaveBeenCalledWith("up"));
    fireEvent.pointerUp(el, { pointerId: 1 });
    await waitFor(() => expect(client.releaseJog).toHaveBeenCalledWith("up"));
  });

  it("does not call releaseJog when hold was rejected by the server", async () => {
    vi.mocked(client.jogHold).mockResolvedValue({
      ok: false,
      body: { error: "command_rejected", reason: "concurrent_command", message: "busy" },
    });
    renderPad();
    const el = screen.getByLabelText("Jog Down");
    fireEvent.pointerDown(el, { button: 0, pointerId: 2 });
    await waitFor(() => expect(client.jogHold).toHaveBeenCalledWith("down"));
    fireEvent.pointerUp(el, { pointerId: 2 });
    await new Promise((r) => setTimeout(r, 50));
    expect(client.releaseJog).not.toHaveBeenCalled();
  });

  it("calls releaseJog on pointer cancel after hold is established", async () => {
    renderPad();
    const el = screen.getByLabelText("Jog Left");
    fireEvent.pointerDown(el, { button: 0, pointerId: 3 });
    await waitFor(() => expect(client.jogHold).toHaveBeenCalledWith("left"));
    fireEvent.pointerCancel(el, { pointerId: 3 });
    await waitFor(() => expect(client.releaseJog).toHaveBeenCalledWith("left"));
  });

  it("ignores non-primary pointer buttons", async () => {
    renderPad();
    fireEvent.pointerDown(screen.getByLabelText("Jog Right"), { button: 2, pointerId: 4 });
    await new Promise((r) => setTimeout(r, 20));
    expect(client.jogHold).not.toHaveBeenCalled();
  });

  it("handles two simultaneous directions independently", async () => {
    vi.mocked(client.releaseJog).mockResolvedValue({ ok: true, duration_ms: 30 });
    renderPad();
    const upEl = screen.getByLabelText("Jog Up");
    const downEl = screen.getByLabelText("Jog Down");
    fireEvent.pointerDown(upEl, { button: 0, pointerId: 10 });
    fireEvent.pointerDown(downEl, { button: 0, pointerId: 11 });
    await waitFor(() => expect(client.jogHold).toHaveBeenCalledTimes(2));
    fireEvent.pointerUp(upEl, { pointerId: 10 });
    await waitFor(() => expect(client.releaseJog).toHaveBeenCalledWith("up"));
    fireEvent.pointerUp(downEl, { pointerId: 11 });
    await waitFor(() => expect(client.releaseJog).toHaveBeenCalledWith("down"));
  });
});
