import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SettingsPage } from "./SettingsPage";

describe("SettingsPage", () => {
  it("renders section headings", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Appearance")).toBeInTheDocument();
    expect(screen.getByText("Control")).toBeInTheDocument();
    expect(screen.getByText("About")).toBeInTheDocument();
  });

  it("renders setting rows", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Theme")).toBeInTheDocument();
    expect(screen.getByText("Default operating mode")).toBeInTheDocument();
  });
});
