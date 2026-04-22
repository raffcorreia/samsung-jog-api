import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { ColorCheckPage } from "./ColorCheckPage";

function renderPage() {
  // Use two history entries so navigate(-1) has somewhere to go.
  return render(
    <MemoryRouter initialEntries={["/", "/color-check"]} initialIndex={1}>
      <Routes>
        <Route path="/color-check" element={<ColorCheckPage />} />
        <Route path="*" element={<div data-testid="other-page" />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ColorCheckPage", () => {
  it("renders the page with the hint text", () => {
    renderPage();
    expect(screen.getByTestId("color-check-page")).toBeInTheDocument();
    expect(screen.getByTestId("color-check-hint")).toBeInTheDocument();
  });

  it("renders all six color swatches", () => {
    renderPage();
    expect(screen.getByTestId("swatch-red")).toBeInTheDocument();
    expect(screen.getByTestId("swatch-green")).toBeInTheDocument();
    expect(screen.getByTestId("swatch-blue")).toBeInTheDocument();
    expect(screen.getByTestId("swatch-white")).toBeInTheDocument();
    expect(screen.getByTestId("swatch-black")).toBeInTheDocument();
    expect(screen.getByTestId("swatch-gray-50%")).toBeInTheDocument();
  });

  it("renders the readability sample", () => {
    renderPage();
    expect(screen.getByTestId("readability-sample")).toBeInTheDocument();
  });

  it("navigates back when the outer page area is clicked", async () => {
    renderPage();
    // Click the outer .page div (not the inner panel which stopPropagates).
    const page = screen.getByTestId("color-check-page");
    // Directly dispatch a click on the outer element itself.
    await userEvent.click(page, { pointerEventsCheck: 0 });
    expect(screen.getByTestId("other-page")).toBeInTheDocument();
  });
});
