import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { TopBar } from "./TopBar";

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
  it("renders the power button", () => {
    renderTopBar();
    expect(screen.getByRole("button", { name: /power/i })).toBeInTheDocument();
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
    let path = "/";
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
    void path; // suppress unused warning
  });
});
