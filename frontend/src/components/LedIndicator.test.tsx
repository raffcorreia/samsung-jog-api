import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LedIndicator } from "./LedIndicator";

describe("LedIndicator", () => {
  it("renders with data-led=off when on=false", () => {
    render(<LedIndicator on={false} />);
    expect(screen.getByTestId("led-indicator")).toHaveAttribute("data-led", "off");
  });

  it("renders with data-led=on when on=true", () => {
    render(<LedIndicator on={true} />);
    expect(screen.getByTestId("led-indicator")).toHaveAttribute("data-led", "on");
  });

  it("has correct aria-label when off", () => {
    render(<LedIndicator on={false} />);
    expect(screen.getByRole("status", { name: "LED off" })).toBeInTheDocument();
  });

  it("has correct aria-label when on", () => {
    render(<LedIndicator on={true} />);
    expect(screen.getByRole("status", { name: "LED on" })).toBeInTheDocument();
  });
});
