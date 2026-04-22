import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { TopBar } from "./TopBar";

// Stub display API so tests don't hit the network.
vi.mock("../api/client", () => ({
  fetchDisplayPower: vi.fn().mockResolvedValue({ on: true, brightness_pct: 30 }),
  setDisplayPower: vi.fn().mockResolvedValue({ on: true, brightness_pct: 30 }),
}));

function renderTopBar(title?: string, initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="*" element={<TopBar title={title} />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("TopBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the power button", () => {
    renderTopBar();
    expect(screen.getByTestId("top-bar-power")).toBeInTheDocument();
  });

  it("renders a clock in HH:MM format", () => {
    renderTopBar();
    const clock = screen.getByTestId("top-bar-clock");
    expect(clock).toBeInTheDocument();
    expect(clock.textContent).toMatch(/^\d{2}:\d{2}$/);
  });

  it("renders the settings cog button", () => {
    renderTopBar();
    expect(screen.getByTestId("top-bar-settings")).toBeInTheDocument();
  });

  it("does not render a back button when no title is given (home screen)", () => {
    renderTopBar();
    expect(screen.queryByTestId("top-bar-back")).not.toBeInTheDocument();
  });

  it("renders back button with title text when title is provided", () => {
    renderTopBar("Settings");
    const back = screen.getByTestId("top-bar-back");
    const title = screen.getByTestId("top-bar-title");
    expect(back).toBeInTheDocument();
    expect(back).toHaveAttribute("aria-label", "Back to home");
    expect(title).toHaveTextContent("Settings");
  });

  it("navigates to /settings when cog is clicked", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route
            path="*"
            element={
              <>
                <TopBar />
                <Routes>
                  <Route path="/settings" element={<div data-testid="settings-page" />} />
                </Routes>
              </>
            }
          />
        </Routes>
      </MemoryRouter>,
    );
    await user.click(screen.getByTestId("top-bar-settings"));
    expect(screen.queryByTestId("settings-page")).toBeInTheDocument();
  });

  it("opens the power menu when the power button is clicked and display is on", async () => {
    const user = userEvent.setup();
    renderTopBar();
    // Wait for the initial fetchDisplayPower to resolve.
    await screen.findByTestId("top-bar-power");
    await user.click(screen.getByTestId("top-bar-power"));
    // PowerMenu should be visible.
    expect(screen.getByTestId("power-menu-display")).toBeInTheDocument();
  });
});
