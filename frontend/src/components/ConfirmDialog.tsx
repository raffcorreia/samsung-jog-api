import { Popup } from "./Popup";

import styles from "./ConfirmDialog.module.css";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Yes",
  cancelLabel = "No",
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Popup
      open={open}
      onClose={onCancel}
      position="center"
      size="confirm"
      blockBackground={true}
      title={title}
    >
      <div className={styles.body}>
        <p className={styles.message}>{message}</p>
        <div className={styles.actions}>
          <button className={styles.secondary} type="button" onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </button>
          <button className={styles.primary} type="button" onClick={onConfirm} disabled={busy}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </Popup>
  );
}
