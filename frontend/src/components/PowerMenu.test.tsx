import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { PowerMenu } from "./PowerMenu";

// Stub API calls so tests don't hit the network.
vi.mock("../api/client", () => ({
  setDisplayPower: vi.fn().mockResolvedValue({ on: false, brightness_pct: 0 }),
  requestShutdown: vi.fn().mockResolvedValue({ ok: true, message: "Shutdown initiated" }),
}));

function renderMenu(props: Partial<Parameters<typeof PowerMenu>[0]> = {}) {
  return render(
    <MemoryRouter>
      <PowerMenu
        open={true}
        displayOn={true}
        onClose={vi.fn()}
        onDisplayToggled={vi.fn()}
        {...props}
      />
    </MemoryRouter>,
  );
}

describe("PowerMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the three choice buttons when open", () => {
    renderMenu();
    expect(screen.getByTestId("power-menu-display")).toBeInTheDocument();
    expect(screen.getByTestId("power-menu-pi")).toBeInTheDocument();
    expect(screen.getByTestId("power-menu-cancel")).toBeInTheDocument();
  });

  it("shows 'Display off' when display is on", () => {
    renderMenu({ displayOn: true });
    expect(screen.getByTestId("power-menu-display")).toHaveTextContent("Display off");
  });

  it("shows 'Display on' when display is off", () => {
    renderMenu({ displayOn: false });
    expect(screen.getByTestId("power-menu-display")).toHaveTextContent("Display on");
  });

  it("calls onClose when Cancel is clicked", async () => {
    const onClose = vi.fn();
    renderMenu({ onClose });
    await userEvent.click(screen.getByTestId("power-menu-cancel"));
    expect(onClose).toHaveBeenCalled();
  });

  it("opens shutdown confirm when Pi is clicked", async () => {
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-pi"));
    expect(screen.getByTestId("shutdown-countdown")).toBeInTheDocument();
    expect(screen.getByTestId("shutdown-now")).toBeInTheDocument();
    expect(screen.getByTestId("shutdown-cancel")).toBeInTheDocument();
  });

  it("shows countdown starting at 5", async () => {
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-pi"));
    expect(screen.getByTestId("shutdown-countdown").textContent).toBe("5");
  });

  it("calls requestShutdown when Now is clicked", async () => {
    const { requestShutdown } = await import("../api/client");
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-pi"));
    await userEvent.click(screen.getByTestId("shutdown-now"));
    expect(requestShutdown).toHaveBeenCalled();
  });

  it("returns to menu when Cancel is clicked on shutdown confirm", async () => {
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-pi"));
    expect(screen.getByTestId("shutdown-countdown")).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("shutdown-cancel"));
    // Should return to power menu choices
    expect(screen.getByTestId("power-menu-display")).toBeInTheDocument();
  });

  it("does not render anything when closed", () => {
    renderMenu({ open: false });
    expect(screen.queryByTestId("power-menu-display")).not.toBeInTheDocument();
  });
});
