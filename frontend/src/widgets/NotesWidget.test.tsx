import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NotesWidget } from "./NotesWidget";

describe("NotesWidget", () => {
  it("renders the header", () => {
    render(<NotesWidget />);
    expect(screen.getByText("Notes")).toBeInTheDocument();
  });

  it("renders all mock note titles", () => {
    render(<NotesWidget />);
    expect(screen.getByText("PiP sequence")).toBeInTheDocument();
    expect(screen.getByText("Input cycling")).toBeInTheDocument();
    expect(screen.getByText("OSD timeout")).toBeInTheDocument();
    expect(screen.getByText("LED blink")).toBeInTheDocument();
  });

  it("renders note body text", () => {
    render(<NotesWidget />);
    expect(screen.getByText(/Center → wait LED/)).toBeInTheDocument();
  });
});
