import { createPortal } from "react-dom";
import { useEffect, useRef, type ReactNode, type RefObject } from "react";

import styles from "./Popup.module.css";

export type PopupPosition = "center" | "right" | "left";
export type PopupSize = "default" | "workspace" | "confirm";

export interface PopupProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  /** Preferred position on screen. Default: "center". */
  position?: PopupPosition;
  /**
   * Clicks on or inside this element will NOT dismiss the popup.
   * Use this when the parent widget (e.g. JogPad) should stay interactive
   * while the popup is open.
   */
  ignoreRef?: RefObject<HTMLElement | null>;
  title?: string;
  size?: PopupSize;
  blockBackground?: boolean;
}

/**
 * Reusable popup template — renders in a portal on document.body.
 *
 * Dismissal rules:
 * - Click X button → closes.
 * - pointerdown anywhere outside the panel AND outside ignoreRef → closes.
 * - pointerdown inside the popup panel → does NOT close.
 * - pointerdown on/inside ignoreRef element → does NOT close (widget stays interactive).
 *
 * The visual backdrop has pointer-events:none so underlying widgets (JogPad)
 * receive their events normally when ignoreRef is set.
 */
export function Popup({
  open,
  onClose,
  children,
  position = "center",
  ignoreRef,
  title,
  size = "default",
  blockBackground = false,
}: PopupProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  // Keep a stable ref to onClose so the effect doesn't need to re-register on every render.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const handler = (e: PointerEvent) => {
      const target = e.target as Node;
      if (panelRef.current?.contains(target)) return;
      if (ignoreRef?.current?.contains(target)) return;
      if (target instanceof Element) {
        const otherPopup = target.closest("[data-popup-panel]");
        if (otherPopup && otherPopup !== panelRef.current) return;
      }
      onCloseRef.current();
    };
    document.addEventListener("pointerdown", handler, true);
    return () => document.removeEventListener("pointerdown", handler, true);
  }, [open, ignoreRef]);

  if (!open) return null;

  const posClass = styles[`pos${position.charAt(0).toUpperCase()}${position.slice(1)}`];
  const sizeClass = styles[`size${size.charAt(0).toUpperCase()}${size.slice(1)}`];
  const backdropClass = blockBackground ? styles.backdropModal : styles.backdropPassThrough;

  return createPortal(
    <>
      <div className={`${styles.backdrop} ${backdropClass}`} aria-hidden="true" />

      <div
        ref={panelRef}
        className={`${styles.panel} ${posClass ?? ""} ${sizeClass ?? ""}`}
        data-popup-panel
        role="dialog"
        aria-modal="true"
        aria-label={title ?? "popup"}
        data-testid="popup-panel"
      >
        <div className={styles.header}>
          {title ? (
            <span className={styles.title}>{title}</span>
          ) : (
            <span />
          )}
          <button
            className={styles.closeBtn}
            type="button"
            aria-label="Close"
            onClick={onClose}
            data-testid="popup-close"
          >
            <svg
              viewBox="0 0 24 24"
              width="16"
              height="16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className={styles.body}>{children}</div>
      </div>
    </>,
    document.body,
  );
}
