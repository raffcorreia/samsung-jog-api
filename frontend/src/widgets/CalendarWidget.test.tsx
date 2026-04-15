import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CalendarWidget } from "./CalendarWidget";

describe("CalendarWidget", () => {
  it("renders the month header", () => {
    render(<CalendarWidget />);
    expect(screen.getByText("April 2026")).toBeInTheDocument();
  });

  it("renders day-of-week labels", () => {
    render(<CalendarWidget />);
    expect(screen.getByRole("columnheader", { name: "Mo" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Su" })).toBeInTheDocument();
  });

  it("marks today (15) with aria-current=date", () => {
    render(<CalendarWidget />);
    const todayCell = screen.getByRole("gridcell", { name: "15" });
    expect(todayCell).toHaveAttribute("aria-current", "date");
  });

  it("renders mock events for today", () => {
    render(<CalendarWidget />);
    expect(screen.getByText("Deck bring-up")).toBeInTheDocument();
  });
});
