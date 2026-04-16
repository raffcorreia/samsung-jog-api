import { useEffect, useMemo, useRef, useState } from "react";

import type { DeckEventsState } from "../hooks/useDeckEvents";
import type { RecordingSummary } from "../types";

import styles from "./RecordingWorkspace.module.css";

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) {
    return ts;
  }
  return d.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export interface RecordingWorkspaceProps {
  deck: DeckEventsState;
  onRequestDelete: (item: RecordingSummary) => void;
}

export function RecordingWorkspace({ deck, onRequestDelete }: RecordingWorkspaceProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selected = useMemo(
    () => deck.recordings.items.find((item) => item.id === selectedId) ?? deck.recordings.items[0] ?? null,
    [deck.recordings.items, selectedId],
  );

  useEffect(() => {
    if (!selected && selectedId !== null) {
      setSelectedId(null);
      setRenamingId(null);
      setRenameDraft("");
      return;
    }
    if (selected && selected.id !== selectedId) {
      setSelectedId(selected.id);
    }
  }, [selected, selectedId]);

  const modeLabel =
    deck.recordingState.mode === "recording"
      ? "recording"
      : deck.recordingState.mode === "replaying"
        ? "replaying"
        : "idle";

  const beginRename = (item: RecordingSummary) => {
    setRenamingId(item.id);
    setRenameDraft(item.name);
  };

  const commitRename = async () => {
    if (!selected || !renamingId) {
      return;
    }
    const nextName = renameDraft.trim();
    if (!nextName) {
      return;
    }
    setBusy(true);
    try {
      const ok = await deck.renameRecording(renamingId, nextName);
      if (ok) {
        setRenamingId(null);
        setRenameDraft("");
      }
    } finally {
      setBusy(false);
    }
  };

  const triggerUpload = () => {
    inputRef.current?.click();
  };

  return (
    <div className={styles.workspace}>
      <div className={styles.hero}>
        <div>
          <div className={styles.eyebrow}>Recording Workspace</div>
          <h2 className={styles.title}>Capture, replay, and manage macros from the observation bus.</h2>
        </div>
        <div className={styles.statusCard} data-mode={deck.recordingState.mode}>
          <span className={styles.statusDot} />
          <div className={styles.statusText}>
            <strong>{modeLabel}</strong>
            <span>
              {deck.recordingState.active_name ?? "No active sequence"}
              {deck.recordingState.mode === "recording"
                ? ` • ${deck.recordingState.event_count} events`
                : ""}
            </span>
          </div>
        </div>
      </div>

      <div className={styles.controls}>
        <button
          className={`${styles.actionButton} ${styles.recordAction}`}
          type="button"
          disabled={busy || deck.recordingState.mode === "replaying"}
          onClick={async () => {
            setBusy(true);
            try {
              if (deck.recordingState.mode === "recording") {
                await deck.stopRecording();
              } else {
                await deck.startRecording();
              }
            } finally {
              setBusy(false);
            }
          }}
        >
          {deck.recordingState.mode === "recording" ? "Stop and Save" : "Start Recording"}
        </button>
        <button
          className={styles.actionButton}
          type="button"
          disabled={busy || !selected || deck.recordingState.mode === "recording"}
          onClick={async () => {
            if (!selected) {
              return;
            }
            setBusy(true);
            try {
              if (deck.recordingState.mode === "replaying") {
                await deck.stopRecordingPlayback();
              } else {
                await deck.playRecording(selected.id);
              }
            } finally {
              setBusy(false);
            }
          }}
        >
          {deck.recordingState.mode === "replaying" ? "Stop Playback" : "Play Selected"}
        </button>
        <button
          className={styles.actionButton}
          type="button"
          disabled={busy}
          onClick={triggerUpload}
        >
          Upload
        </button>
        <input
          ref={inputRef}
          className={styles.hiddenInput}
          type="file"
          accept="application/json,.json"
          onChange={async (event) => {
            const file = event.target.files?.[0];
            if (!file) {
              return;
            }
            setBusy(true);
            try {
              await deck.uploadRecording(file);
            } finally {
              event.target.value = "";
              setBusy(false);
            }
          }}
        />
      </div>

      {deck.recordingState.last_error ? (
        <div className={styles.errorBanner}>{deck.recordingState.last_error}</div>
      ) : null}

      <div className={styles.grid}>
        <div className={styles.libraryPane}>
          <div className={styles.sectionHeader}>
            <span>Library</span>
            <span>{deck.recordings.items.length} items</span>
          </div>
          <div className={styles.list} role="list">
            {deck.recordings.items.length === 0 ? (
              <div className={styles.emptyState}>
                No recordings yet. Start a capture and it will save with date and time.
              </div>
            ) : null}
            {deck.recordings.items.map((item) => {
              const isSelected = selected?.id === item.id;
              const isRenaming = renamingId === item.id;
              return (
                <div
                  key={item.id}
                  className={styles.listItem}
                  data-selected={isSelected}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedId(item.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedId(item.id);
                    }
                  }}
                >
                  <div className={styles.itemTop}>
                    {isRenaming ? (
                      <input
                        className={styles.renameInput}
                        value={renameDraft}
                        onChange={(event) => setRenameDraft(event.target.value)}
                        onClick={(event) => event.stopPropagation()}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            void commitRename();
                          }
                          if (event.key === "Escape") {
                            setRenamingId(null);
                            setRenameDraft("");
                          }
                        }}
                      />
                    ) : (
                      <strong>{item.name}</strong>
                    )}
                    <span>{formatDuration(item.duration_ms)}</span>
                  </div>
                  <div className={styles.itemMeta}>
                    <span>{item.event_count} events</span>
                    <span>{formatTimestamp(item.updated_at)}</span>
                  </div>
                  {isSelected ? (
                    <div className={styles.inlineActions}>
                      {isRenaming ? (
                        <>
                          <button
                            className={styles.inlineButton}
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              void commitRename();
                            }}
                            disabled={busy || renameDraft.trim().length === 0}
                          >
                            Save
                          </button>
                          <button
                            className={styles.inlineButton}
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              setRenamingId(null);
                              setRenameDraft("");
                            }}
                            disabled={busy}
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <a
                            className={styles.inlineButton}
                            href={deck.recordingDownloadUrl(item.id)}
                            download={item.filename}
                            onClick={(event) => event.stopPropagation()}
                          >
                            Download
                          </a>
                          <button
                            className={styles.inlineButton}
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              beginRename(item);
                            }}
                            disabled={busy || deck.recordingState.mode !== "idle"}
                          >
                            Rename
                          </button>
                        </>
                      )}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>

        <div className={styles.detailPane}>
          <div className={styles.sectionHeader}>
            <span>Details</span>
            <span>{selected ? selected.filename : "No selection"}</span>
          </div>
          {selected ? (
            <div className={styles.detailCard}>
              <div className={styles.detailRow}>
                <span>Name</span>
                <strong>{selected.name}</strong>
              </div>
              <div className={styles.detailRow}>
                <span>Created</span>
                <strong>{formatTimestamp(selected.created_at)}</strong>
              </div>
              <div className={styles.detailRow}>
                <span>Updated</span>
                <strong>{formatTimestamp(selected.updated_at)}</strong>
              </div>
              <div className={styles.detailRow}>
                <span>Duration</span>
                <strong>{formatDuration(selected.duration_ms)}</strong>
              </div>
              <div className={styles.detailRow}>
                <span>Events</span>
                <strong>{selected.event_count}</strong>
              </div>
              <div className={styles.detailRow}>
                <span>File size</span>
                <strong>{formatBytes(selected.size_bytes)}</strong>
              </div>
              <div className={styles.detailActions}>
                <a
                  className={styles.inlineButton}
                  href={deck.recordingDownloadUrl(selected.id)}
                  download={selected.filename}
                >
                  Download
                </a>
                <button
                  className={`${styles.inlineButton} ${styles.deleteButton}`}
                  type="button"
                  disabled={busy || deck.recordingState.mode !== "idle"}
                  onClick={() => onRequestDelete(selected)}
                >
                  Delete
                </button>
              </div>
            </div>
          ) : (
            <div className={styles.emptyDetail}>Select a recording to inspect or replay it.</div>
          )}
        </div>
      </div>
    </div>
  );
}
