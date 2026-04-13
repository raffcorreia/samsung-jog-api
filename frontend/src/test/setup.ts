import "@testing-library/jest-dom/vitest";

if (
  typeof window !== "undefined" &&
  typeof window.HTMLElement.prototype.scrollIntoView !== "function"
) {
  window.HTMLElement.prototype.scrollIntoView = () => {};
}

// jsdom does not provide PointerEvent; React `onPointerDown`/`onPointerUp` need it for tests.
if (typeof window !== "undefined" && !window.PointerEvent) {
  class PE extends MouseEvent {
    readonly pointerId: number;
    readonly pointerType: string;
    readonly width = 1;
    readonly height = 1;
    readonly pressure = 0;
    readonly tangentialPressure = 0;
    readonly tiltX = 0;
    readonly tiltY = 0;
    readonly twist = 0;
    readonly isPrimary = true;
    readonly altitudeAngle = 0;
    readonly azimuthAngle = 0;
    getCoalescedEvents(): PointerEvent[] {
      return [];
    }
    getPredictedEvents(): PointerEvent[] {
      return [];
    }
    constructor(type: string, init?: PointerEventInit) {
      super(type, init);
      this.pointerId = init?.pointerId ?? 0;
      this.pointerType = init?.pointerType ?? "mouse";
    }
  }
  Object.assign(window, { PointerEvent: PE as unknown as typeof PointerEvent });
}
