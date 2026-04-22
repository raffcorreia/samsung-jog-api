import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { SettingsPage } from "./SettingsPage";

// Stub display API so tests don't hit the network.
vi.mock("../api/client", () => ({
  fetchDisplayBrightness: vi.fn().mockResolvedValue({
    brightness_pct: 30,
    brightness_raw: 51,
    max_raw: 170,
  }),
  setDisplayBrightness: vi.fn().mockResolvedValue({
    brightness_pct: 30,
    brightness_raw: 51,
    max_raw: 170,
  }),
}));

function renderSettings() {
  return render(
    <MemoryRouter>
      <SettingsPage />
    </MemoryRouter>,
  );
}

describe("SettingsPage", () => {
  it("renders section headings", () => {
    renderSettings();
    expect(screen.getByText("Appearance")).toBeInTheDocument();
    expect(screen.getByText("Control")).toBeInTheDocument();
    expect(screen.getByText("About")).toBeInTheDocument();
  });

  it("renders setting rows", () => {
    renderSettings();
    expect(screen.getByText("Theme")).toBeInTheDocument();
    expect(screen.getByText("Default operating mode")).toBeInTheDocument();
  });

  it("renders the Display section with brightness slider", () => {
    renderSettings();
    expect(screen.getByText("Display")).toBeInTheDocument();
    expect(screen.getByTestId("brightness-slider")).toBeInTheDocument();
  });

  it("renders the color-check open button", () => {
    renderSettings();
    expect(screen.getByTestId("open-color-check")).toBeInTheDocument();
  });
});
