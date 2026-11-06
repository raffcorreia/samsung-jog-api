import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LedCommunicationStatus, MonitorCommandResult } from "../types";
import { LedCommunicationWidget } from "./LedCommunicationWidget";

const { addLedCommunicationNote, clearLedCommunication, fetchLedCommunicationStatus, sendMonitorCommand } = vi.hoisted(() => ({
  addLedCommunicationNote: vi.fn(),
  clearLedCommunication: vi.fn(),
  fetchLedCommunicationStatus: vi.fn(),
  sendMonitorCommand: vi.fn(),
}));

vi.mock("../api/client", () => ({
  addLedCommunicationNote,
  clearLedCommunication,
  fetchLedCommunicationStatus,
  holdCommunicationHighForMeasurement: vi.fn(),
  ledCommunicationExportUrl: vi.fn(() => "/export"),
  replayLedCommunication: vi.fn(),
  sendMonitorCommand,
  startLedCommunication: vi.fn(),
  stopLedCommunication: vi.fn(),
}));

const status: LedCommunicationStatus = {
  capturing: true,
  level: null,
  accepted_edges: 0,
  rejected_glitches: 0,
  overruns: 0,
  buffered_edges: 0,
  buffer_size: 4096,
  glitch_ns: 1_000_000,
  half_bit_ns: 10_000_000,
  tolerance: 0.45,
  intervals: { min_ns: null, median_ns: null, max_ns: null },
  valid_frames: 0,
  missing_frames: 0,
  decoder_rejections: 0,
  latest_frame: null,
  tx_history: [],
};

describe("LedCommunicationWidget command controls", () => {
  it("offers the 1008.7 TB refresh command", () => {
    render(<LedCommunicationWidget state={{ status, edges: [], frames: [] }} />);
    expect(screen.getByRole("option", { name: "TB refresh · A5 EE" })).toHaveValue("11");
  });

  it("defaults to 25 ms and normalizes empty or zero only after editing finishes", async () => {
    const user = userEvent.setup();
    render(<LedCommunicationWidget state={{ status, edges: [], frames: [] }} />);
    const speed = screen.getByRole("spinbutton", { name: /Speed/i });

    expect(speed).toHaveValue(25);
    await user.clear(speed);
    expect(speed).toHaveValue(null);
    await user.tab();
    expect(speed).toHaveValue(25);

    await user.clear(speed);
    await user.type(speed, "0");
    expect(speed).toHaveValue(0);
    await user.tab();
    expect(speed).toHaveValue(25);
  });

  it("keeps the message selector enabled while only the send button is transmitting", async () => {
    let finishSend!: (result: MonitorCommandResult) => void;
    sendMonitorCommand.mockReturnValueOnce(new Promise((resolve) => { finishSend = resolve; }));
    fetchLedCommunicationStatus.mockResolvedValue(status);
    const user = userEvent.setup();
    render(<LedCommunicationWidget state={{ status, edges: [], frames: [] }} />);

    await user.click(screen.getByRole("button", { name: "SEND" }));

    expect(screen.getByRole("button", { name: "SENDING…" })).toBeDisabled();
    const selector = screen.getByRole("combobox", { name: /Message/i });
    expect(selector).toBeEnabled();
    await user.selectOptions(selector, "1");
    expect(selector).toHaveValue("1");

    finishSend({
      command_code: 0,
      command_name: "query",
      frame_hex: "a55a",
      bit_time_ms: 25,
      status: "waiting_response",
      state: null,
      diagnostic: null,
      presence: null,
    });
    await waitFor(() => expect(screen.getByRole("button", { name: "SEND" })).toBeEnabled());
  });

  it("decodes 1008.5 DIAG and PRESENCE fields into their documented meanings", async () => {
    const user = userEvent.setup();
    const diagnostic = {
      edge_seq: 113,
      monotonic_ns: 154_005_492_926_273,
      raw_hex: "ffff2dd415365500f8",
      sequence: 54,
      crc: 0xF8,
      message_type: "diag" as const,
      type_code: 0x15,
      diagnostic_reads: 85,
      diagnostic_conversions_stopped: false,
      diagnostic_timeouts: 0,
      diagnostic_rejected_frames: 0,
    };
    const presence = {
      edge_seq: 231,
      monotonic_ns: 154_007_204_664_894,
      raw_hex: "ffff2dd4183706bb76",
      sequence: 55,
      crc: 0x76,
      message_type: "presence" as const,
      type_code: 0x18,
      presence_mask: 0x06,
      presence_window0_state: 0x0B,
      presence_window1_state: 0x0B,
    };

    render(
      <LedCommunicationWidget
        state={{ status, edges: [], frames: [diagnostic, presence] }}
      />,
    );

    expect(screen.getByText(/PRESENCE #55/)).toHaveTextContent(
      "TB + DP reported · left picture · right picture · raw mask 0x06",
    );
    await user.click(screen.getByText("Latest received"));
    expect(screen.getByRole("dialog", { name: "Received message history" })).toHaveTextContent(
      "DIAG #54 · 85 ADC reads · conversions running · 0 timeouts · 0 rejected frames",
    );
  });

  it("shows an ordered copyable session and clears every communication view", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    const frame = {
      edge_seq: 31,
      monotonic_ns: 2_000_000_000,
      received_at: "2026-11-05T22:00:01Z",
      raw_hex: "ffff2dd411382326a2",
      sequence: 56,
      crc: 0xA2,
      message_type: "state" as const,
      type_code: 0x11,
      layout: "pbp" as const,
      input1: "tb" as const,
      input2: "dp" as const,
      connection_mask: 6,
    };
    const populatedStatus: LedCommunicationStatus = {
      ...status,
      accepted_edges: 31,
      valid_frames: 1,
      frame_history: [frame],
      tx_history: [{
        command_code: 0,
        command_name: "query",
        frame_hex: "a55a",
        bit_time_ms: 25,
        status: "response",
        monotonic_ns: 1_000_000_000,
        sent_at: "2026-11-05T22:00:00Z",
        samples: [],
        state: frame,
      }],
    };
    clearLedCommunication.mockResolvedValue({ ...status, frame_history: [], tx_history: [] });
    render(<LedCommunicationWidget state={{ status: populatedStatus, edges: [], frames: [frame] }} />);

    expect(screen.getByRole("button", { name: "Pause capture" }).querySelectorAll("rect")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Clear complete capture and session" }).querySelector("svg")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open communication session" }));
    const dialog = screen.getByRole("dialog", { name: "Communication session" });
    expect(dialog).toHaveTextContent("OUT");
    expect(dialog).toHaveTextContent("REQUEST");
    expect(dialog).toHaveTextContent("IN");
    expect(dialog).toHaveTextContent("RESPONSE");
    await user.click(screen.getByRole("button", { name: "Copy all" }));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("OUT  REQUEST"));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("IN   RESPONSE"));
    await user.click(screen.getByRole("button", { name: "Close session" }));

    await user.click(screen.getByRole("button", { name: "Clear complete capture and session" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Open communication session" })).toHaveTextContent("0"));
    expect(screen.getByText("No validated message")).toBeInTheDocument();
  });

  it("falls back to execCommand copy when the HTTP kiosk clipboard API is unavailable", async () => {
    const user = userEvent.setup();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: undefined,
    });
    const execCommand = vi.fn(() => true);
    Object.defineProperty(document, "execCommand", {
      configurable: true,
      value: execCommand,
    });
    const frame = {
      edge_seq: 1,
      monotonic_ns: 2_000_000_000,
      raw_hex: "ffff2dd411382326a2",
      sequence: 56,
      crc: 0xA2,
      message_type: "state" as const,
      type_code: 0x11,
      layout: "pbp" as const,
      input1: "tb" as const,
      input2: "dp" as const,
    };
    render(<LedCommunicationWidget state={{ status, edges: [], frames: [frame] }} />);

    await user.click(screen.getByRole("button", { name: "Open communication session" }));
    await user.click(screen.getByRole("button", { name: "Copy all" }));

    expect(execCommand).toHaveBeenCalledWith("copy");
    expect(screen.getByRole("status")).toHaveTextContent("Copied 1 message");
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("adds timestamped notes to the authoritative session", async () => {
    const user = userEvent.setup();
    addLedCommunicationNote.mockResolvedValue({
      ...status,
      session_history: [{
        id: "note-1",
        timestamp: "2026-11-06T02:53:42.010000Z",
        monotonic_ns: 1,
        direction: "NOTE",
        kind: "NOTE",
        raw_hex: null,
        note: "unplugged DP",
      }],
    });
    render(<LedCommunicationWidget state={{ status, edges: [], frames: [] }} />);

    await user.click(screen.getByRole("button", { name: "Open communication session" }));
    await user.type(screen.getByRole("textbox", { name: "Session note" }), "unplugged DP");
    await user.click(screen.getByRole("button", { name: "ADD NOTE" }));

    await waitFor(() => expect(addLedCommunicationNote).toHaveBeenCalledWith("unplugged DP"));
    expect(screen.getByRole("dialog", { name: "Communication session" })).toHaveTextContent("unplugged DP");
  });
});
