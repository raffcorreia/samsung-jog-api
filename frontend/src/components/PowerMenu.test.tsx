import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { PowerMenu } from "./PowerMenu";

vi.mock("../api/client", () => ({
  setDisplayPower: vi.fn().mockResolvedValue({ on: false, brightness_pct: 0 }),
  requestShutdown: vi.fn().mockResolvedValue({ ok: true, message: "Shutdown initiated" }),
  requestRestart: vi.fn().mockResolvedValue({ ok: true, message: "Restart initiated" }),
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

  it("renders the choice buttons when open", () => {
    renderMenu();
    expect(screen.getByTestId("power-menu-display")).toBeInTheDocument();
    expect(screen.getByTestId("power-menu-reset")).toBeInTheDocument();
    expect(screen.getByTestId("power-menu-poweroff")).toBeInTheDocument();
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

  it("goes to countdown when Reset is clicked", async () => {
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-reset"));
    expect(screen.getByTestId("action-countdown")).toBeInTheDocument();
    expect(screen.getByTestId("countdown-now")).toHaveTextContent("Restart now");

  });

  it("shows countdown starting at 10 for reset", async () => {
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-reset"));
    expect(screen.getByTestId("action-countdown").textContent).toBe("10");
  });

  it("calls requestRestart when countdown-now is clicked after Reset", async () => {
    const { requestRestart } = await import("../api/client");
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-reset"));
    await userEvent.click(screen.getByTestId("countdown-now"));
    expect(requestRestart).toHaveBeenCalled();
  });

  it("shows confirmation dialog when Power off is clicked", async () => {
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-poweroff"));
    expect(screen.getByText(/cannot be restored/i)).toBeInTheDocument();
  });

  it("goes to countdown after confirming power off", async () => {
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-poweroff"));
    await userEvent.click(screen.getByText("Continue"));
    expect(screen.getByTestId("action-countdown")).toBeInTheDocument();
    expect(screen.getByTestId("countdown-now")).toHaveTextContent("Shut down now");
  });

  it("calls requestShutdown when countdown-now is clicked after Power off", async () => {
    const { requestShutdown } = await import("../api/client");
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-poweroff"));
    await userEvent.click(screen.getByText("Continue"));
    await userEvent.click(screen.getByTestId("countdown-now"));
    expect(requestShutdown).toHaveBeenCalled();
  });

  it("returns to menu when Cancel is clicked in confirmation", async () => {
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-poweroff"));
    await userEvent.click(screen.getByText("Cancel"));
    expect(screen.getByTestId("power-menu-display")).toBeInTheDocument();
  });

  it("returns to menu when countdown-cancel is clicked", async () => {
    renderMenu();
    await userEvent.click(screen.getByTestId("power-menu-reset"));
    await userEvent.click(screen.getByTestId("countdown-cancel"));
    expect(screen.getByTestId("power-menu-display")).toBeInTheDocument();
  });

  it("does not render anything when closed", () => {
    renderMenu({ open: false });
    expect(screen.queryByTestId("power-menu-display")).not.toBeInTheDocument();
  });
});
