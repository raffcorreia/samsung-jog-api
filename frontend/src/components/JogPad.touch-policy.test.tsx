import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { JogPad } from "./JogPad";

/**
 * These tests document kiosk/touch expectations. They do not run a real browser,
 * but they lock in DOM hooks and control count so layout/touch refactors stay intentional.
 */
describe("JogPad touch / kiosk contract", () => {
  it("exposes a single jog surface with explicit touch policy metadata", () => {
    render(<JogPad deckBusy={false} onLocalLog={() => {}} />);
    const pad = screen.getByTestId("jog-pad");
    expect(pad).toHaveAttribute("data-touch-policy", "none");
  });

  it("renders five primary jog hit targets (center button + four ring segments)", () => {
    render(<JogPad deckBusy={false} onLocalLog={() => {}} />);
    expect(screen.getAllByLabelText(/^Jog /)).toHaveLength(5);
  });
});
