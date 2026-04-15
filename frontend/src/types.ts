export type JogAction = "up" | "down" | "left" | "right" | "center";

export type OperatingMode = "jog" | "ddc" | "blind";

export type ControlState = "idle" | "commanding";

export type HardwareKind = "live" | "mock";

export type LogLevel = "debug" | "info" | "warning" | "error";

export interface SignalSnapshot {
  key_adc1_active: boolean;
  key_led_active: boolean;
}

export interface StatusPayload {
  version: string;
  hardware: HardwareKind;
  operating_mode: OperatingMode;
  control_state: ControlState;
  signals: SignalSnapshot;
}

export type WsCategory = "command" | "bus" | "control" | "log" | "ddc" | "recording";

export interface WsEventV1 {
  v: 1;
  category: WsCategory;
  type: string;
  ts: string;
  data: Record<string, unknown>;
}

export interface CommandRejectedBody {
  error: "command_rejected";
  reason: string;
  message: string;
}
