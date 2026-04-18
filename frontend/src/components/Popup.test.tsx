import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useRef } from "react";
import { describe, expect, it, vi } from "vitest";

import { Popup } from "./Popup";

describe("Popup", () => {
  it("does not render when open=false", () => {
    render(
      <Popup open={false} onClose={() => {}}>
        <div data-testid="popup-content">hello</div>
      </Popup>,
    );
    expect(screen.queryByTestId("popup-content")).not.toBeInTheDocument();
  });

  it("renders children when open=true", () => {
    render(
      <Popup open={true} onClose={() => {}}>
        <div data-testid="popup-content">hello</div>
      </Popup>,
    );
    expect(screen.getByTestId("popup-content")).toBeInTheDocument();
  });

  it("renders the close button", () => {
    render(
      <Popup open={true} onClose={() => {}}>
        content
      </Popup>,
    );
    expect(screen.getByTestId("popup-close")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <Popup open={true} onClose={onClose}>
        content
      </Popup>,
    );
    await user.click(screen.getByTestId("popup-close"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose on pointerdown outside the panel", () => {
    const onClose = vi.fn();
    render(
      <div>
        <div data-testid="outside" />
        <Popup open={true} onClose={onClose}>
          content
        </Popup>
      </div>,
    );
    fireEvent.pointerDown(screen.getByTestId("outside"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does NOT call onClose on pointerdown inside the panel", () => {
    const onClose = vi.fn();
    render(
      <Popup open={true} onClose={onClose}>
        <div data-testid="inside">content</div>
      </Popup>,
    );
    fireEvent.pointerDown(screen.getByTestId("inside"));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("does NOT call onClose when clicking the ignoreRef element", () => {
    const onClose = vi.fn();

    function Wrapper() {
      const ignoreRef = useRef<HTMLDivElement>(null);
      return (
        <div>
          <div ref={ignoreRef} data-testid="ignore-target">
            JogPad here
          </div>
          <Popup open={true} onClose={onClose} ignoreRef={ignoreRef}>
            content
          </Popup>
        </div>
      );
    }

    render(<Wrapper />);
    fireEvent.pointerDown(screen.getByTestId("ignore-target"));
    expect(onClose).not.toHaveBeenCalled();
  });

  it("renders the title when provided", () => {
    render(
      <Popup open={true} onClose={() => {}} title="OSD">
        content
      </Popup>,
    );
    expect(screen.getByText("OSD")).toBeInTheDocument();
  });

  it("does NOT close a parent popup when clicking inside a nested popup", () => {
    const onParentClose = vi.fn();
    const onChildClose = vi.fn();

    render(
      <>
        <Popup open={true} onClose={onParentClose} title="Parent">
          parent
        </Popup>
        <Popup open={true} onClose={onChildClose} title="Child">
          <button type="button">Confirm</button>
        </Popup>
      </>,
    );

    fireEvent.pointerDown(screen.getByRole("button", { name: "Confirm" }));
    expect(onParentClose).not.toHaveBeenCalled();
    expect(onChildClose).not.toHaveBeenCalled();
  });
});
