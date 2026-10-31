export type JogAction = "up" | "down" | "left" | "right" | "center";

export type OperatingMode = "jog" | "ddc" | "blind";

export type ControlState = "idle" | "commanding";

export type HardwareKind = "live" | "mock";

export type LogLevel = "debug" | "info" | "warning" | "error";

export interface SignalSnapshot {
  key_adc1_active: boolean;
  key_led_active: boolean;
  /** Decoded KEY_ADC2 direction when asserted; null when idle / unknown. */
  key_adc2_direction: "up" | "down" | "left" | "right" | null;
}

export interface StatusPayload {
  version: string;
  hardware: HardwareKind;
  operating_mode: OperatingMode;
  control_state: ControlState;
  signals: SignalSnapshot;
}

export type WsCategory = "command" | "bus" | "control" | "log" | "ddc" | "recording" | "display" | "led_comm";

export interface WsEventV1 {
  v: 1;
  category: WsCategory;
  type: string;
  ts: string;
  data: Record<string, unknown>;
}

export interface LedCommunicationEdge {
  seq: number;
  monotonic_ns: number;
  level: 0 | 1;
  interval_ns: number | null;
}

export interface LedStateFrame {
  edge_seq: number;
  monotonic_ns: number;
  raw_hex: string;
  sequence: number;
  layout: "single" | "pip" | "pbp" | "unknown";
  input1: "none" | "hdmi" | "dp" | "tb" | "unknown";
  input2: "none" | "hdmi" | "dp" | "tb" | "unknown";
  crc: number;
}

export interface LedCommunicationStatus {
  capturing: boolean;
  level: 0 | 1 | null;
  accepted_edges: number;
  rejected_glitches: number;
  overruns: number;
  buffered_edges: number;
  buffer_size: number;
  glitch_ns: number;
  half_bit_ns: number;
  tolerance: number;
  intervals: { min_ns: number | null; median_ns: number | null; max_ns: number | null };
  valid_frames: number;
  missing_frames: number;
  decoder_rejections: number;
  latest_frame: LedStateFrame | null;
}

export interface LedCommunicationState {
  status: LedCommunicationStatus | null;
  edges: readonly LedCommunicationEdge[];
  frames: readonly LedStateFrame[];
}

export interface CommandRejectedBody {
  error: "command_rejected";
  reason: string;
  message: string;
}

export interface RecordingHoldEvent {
  type: "hold";
  action: JogAction;
}

export interface RecordingReleaseEvent {
  type: "release";
  action: JogAction;
}

export interface RecordingDelayEvent {
  type: "delay";
  duration_ms: number;
}

export interface RecordingLedEvent {
  type: "led";
  active: boolean;
  blocking: boolean;
  poll_interval_ms?: number | null;
  timeout_ms?: number | null;
}

export interface RecordingWaitLedEvent {
  type: "wait_led";
  match: { active: boolean };
  poll_interval_ms: number;
  timeout_ms: number;
}

export interface RecordingWaitDdcEvent {
  type: "wait_ddc";
  match: Record<string, unknown>;
  poll_interval_ms: number;
  timeout_ms: number;
}

export type RecordingEvent =
  | RecordingHoldEvent
  | RecordingReleaseEvent
  | RecordingDelayEvent
  | RecordingLedEvent
  | RecordingWaitLedEvent
  | RecordingWaitDdcEvent;

export interface RecordingSummary {
  id: string;
  filename: string;
  name: string;
  created_at: string;
  updated_at: string;
  event_count: number;
  duration_ms: number;
  size_bytes: number;
}

export interface RecordingLibrary {
  items: RecordingSummary[];
}

export interface RecordingState {
  mode: "idle" | "recording" | "replaying";
  recording_started_at: string | null;
  replay_started_at: string | null;
  replay_total_duration_ms: number | null;
  replaying_id: string | null;
  active_name: string | null;
  event_count: number;
  last_error: string | null;
}

export interface RecordingRejectedBody {
  error: "recording_rejected";
  reason: string;
  message: string;
}
