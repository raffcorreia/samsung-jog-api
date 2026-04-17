import { useEffect, useMemo, useRef, useState } from "react";

import type { DeckEventsState } from "../hooks/useDeckEvents";
import type { RecordingSummary } from "../types";

import { ConfirmDialog } from "./ConfirmDialog";
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

function ReplayProgressIcon({ progress }: { progress: number }) {
  const radius = 11;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.max(0, Math.min(1, progress)));
  return (
    <span className={styles.progressIcon} aria-hidden="true">
      <svg viewBox="0 0 32 32" className={styles.progressSvg}>
        <circle cx="16" cy="16" r={radius} className={styles.progressTrack} />
        <circle
          cx="16"
          cy="16"
          r={radius}
          className={styles.progressValue}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <span className={styles.progressStopGlyph} />
    </span>
  );
}

function RecordingStatusIcon({
  mode,
}: {
  mode: DeckEventsState["recordingState"]["mode"];
}) {
  return (
    <svg
      className={styles.statusIcon}
      viewBox="0 0 96 72"
      aria-hidden="true"
      data-mode={mode}
    >
      <rect x="8" y="10" width="80" height="52" rx="12" className={styles.cassetteBody} />
      <rect x="18" y="16" width="60" height="10" rx="4" className={styles.cassetteLabel} />
      <rect x="19" y="28" width="58" height="18" rx="5" className={styles.cassetteWindow} />
      <path d="M27 36h42" className={styles.cassetteTape} />
      <path d="M34 36h8" className={styles.cassetteGuide} />
      <path d="M54 36h8" className={styles.cassetteGuide} />
      <circle cx="31" cy="37" r="8.5" className={styles.cassetteReel} />
      <circle cx="65" cy="37" r="8.5" className={styles.cassetteReel} />
      <circle cx="31" cy="37" r="2.6" className={styles.cassetteHub} />
      <circle cx="65" cy="37" r="2.6" className={styles.cassetteHub} />
      <circle cx="18" cy="56" r="1.8" className={styles.cassetteScrew} />
      <circle cx="78" cy="56" r="1.8" className={styles.cassetteScrew} />
      <path d="M26 52h12l-4 8h-8Z" className={styles.cassetteBase} />
      <path d="M70 52H58l4 8h8Z" className={styles.cassetteBase} />
    </svg>
  );
}

function ActionIcon({
  kind,
}: {
  kind:
    | "record"
    | "stop"
    | "play"
    | "upload"
    | "download"
    | "rename"
    | "edit"
    | "delete"
    | "save"
    | "cancel"
    | "close";
}) {
  if (kind === "record") {
    return <span className={styles.recordGlyph} aria-hidden="true" />;
  }
  if (kind === "stop") {
    return <span className={styles.stopGlyph} aria-hidden="true" />;
  }
  if (kind === "play") {
    return <span className={styles.playGlyph} aria-hidden="true" />;
  }
  if (kind === "upload") {
    return (
      <svg viewBox="0 0 24 24" className={styles.iconSvg} aria-hidden="true">
        <path d="M12 16V5" />
        <path d="m7 10 5-5 5 5" />
        <path d="M5 19h14" />
      </svg>
    );
  }
  if (kind === "download") {
    return (
      <svg viewBox="0 0 24 24" className={styles.iconSvg} aria-hidden="true">
        <path d="M12 5v11" />
        <path d="m17 11-5 5-5-5" />
        <path d="M5 19h14" />
      </svg>
    );
  }
  if (kind === "rename") {
    return (
      <svg viewBox="0 0 24 24" className={styles.iconSvg} aria-hidden="true">
        <path d="M6 18.5V14l7.9-7.9 4 4-7.9 7.9H6Z" />
        <path d="m12.9 7 4 4" />
      </svg>
    );
  }
  if (kind === "edit") {
    return (
      <svg viewBox="0 0 24 24" className={styles.iconSvg} aria-hidden="true">
        <path d="M8 6h10" />
        <path d="M8 12h8" />
        <path d="M8 18h10" />
        <path d="m4 19 1.1-3.9L12.8 7.4l2.8 2.8-7.7 7.7L4 19Z" />
      </svg>
    );
  }
  if (kind === "save") {
    return (
      <svg viewBox="0 0 24 24" className={styles.iconSvg} aria-hidden="true">
        <path d="M5 12.5 10 17l9-10" />
      </svg>
    );
  }
  if (kind === "cancel") {
    return (
      <svg viewBox="0 0 24 24" className={styles.iconSvg} aria-hidden="true">
        <path d="M7 7h10v10H7z" />
        <path d="M4.5 12h-1" />
      </svg>
    );
  }
  if (kind === "close") {
    return (
      <svg viewBox="0 0 24 24" className={styles.iconSvg} aria-hidden="true">
        <path d="M18 6 6 18" />
        <path d="m6 6 12 12" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" className={styles.iconSvg} aria-hidden="true">
      <path d="M6 7h12" />
      <path d="M9 7V5h6v2" />
      <path d="M8 7v12h8V7" />
    </svg>
  );
}

export function RecordingWorkspace({ deck, onRequestDelete }: RecordingWorkspaceProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editorOriginal, setEditorOriginal] = useState("");
  const [editorDraft, setEditorDraft] = useState("");
  const [closeEditorConfirmOpen, setCloseEditorConfirmOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const selected = useMemo(
    () => deck.recordings.items.find((item) => item.id === selectedId) ?? deck.recordings.items[0] ?? null,
    [deck.recordings.items, selectedId],
  );
  const isEditorOpen = editingId !== null && selected?.id === editingId;
  const editorDirty = isEditorOpen && editorDraft !== editorOriginal;
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (!selected && selectedId !== null) {
      setSelectedId(null);
      setRenamingId(null);
      setRenameDraft("");
      setEditingId(null);
      setEditorOriginal("");
      setEditorDraft("");
      setCloseEditorConfirmOpen(false);
      return;
    }
    if (selected && selected.id !== selectedId) {
      setSelectedId(selected.id);
    }
  }, [selected, selectedId]);

  useEffect(() => {
    if (deck.recordingState.mode !== "replaying") {
      return;
    }
    const timer = window.setInterval(() => {
      setNowMs(Date.now());
    }, 120);
    return () => {
      window.clearInterval(timer);
    };
  }, [deck.recordingState.mode]);

  const modeLabel =
    deck.recordingState.mode === "recording"
      ? "recording"
      : deck.recordingState.mode === "replaying"
        ? "replaying"
        : "ready";

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

  const replayProgress =
    deck.recordingState.mode === "replaying" &&
    deck.recordingState.replay_started_at &&
    deck.recordingState.replay_total_duration_ms &&
    deck.recordingState.replay_total_duration_ms > 0
      ? Math.max(
          0,
          Math.min(
            1,
            (nowMs - new Date(deck.recordingState.replay_started_at).getTime()) /
              deck.recordingState.replay_total_duration_ms,
          ),
        )
      : 0;

  const beginEdit = async (item: RecordingSummary) => {
    setBusy(true);
    try {
      const content = await deck.fetchRecordingContent(item.id);
      if (content === null) {
        return;
      }
      setSelectedId(item.id);
      setEditingId(item.id);
      setEditorOriginal(content);
      setEditorDraft(content);
      setRenamingId(null);
      setRenameDraft("");
    } finally {
      setBusy(false);
    }
  };

  const saveEditor = async () => {
    if (!selected || !isEditorOpen) {
      return false;
    }
    setBusy(true);
    try {
      const ok = await deck.updateRecordingContent(selected.id, editorDraft);
      if (!ok) {
        return false;
      }
      const content = await deck.fetchRecordingContent(selected.id);
      if (content !== null) {
        setEditorOriginal(content);
        setEditorDraft(content);
      }
      return true;
    } finally {
      setBusy(false);
    }
  };

  const cancelEditorChanges = () => {
    setEditorDraft(editorOriginal);
  };

  const closeEditor = () => {
    setEditingId(null);
    setEditorOriginal("");
    setEditorDraft("");
    setCloseEditorConfirmOpen(false);
  };

  return (
    <div className={styles.workspace}>
      <div className={styles.hero}>
        <div className={styles.controls}>
          <button
            className={`${styles.actionButton} ${styles.recordAction} ${styles.iconButton}`}
            type="button"
            disabled={busy || deck.recordingState.mode === "replaying"}
            aria-label={deck.recordingState.mode === "recording" ? "Stop and save recording" : "Start recording"}
            title={deck.recordingState.mode === "recording" ? "Stop and save recording" : "Start recording"}
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
            <ActionIcon kind={deck.recordingState.mode === "recording" ? "stop" : "record"} />
          </button>
          <button
            className={`${styles.actionButton} ${styles.iconButton}`}
            type="button"
            disabled={busy || !selected || deck.recordingState.mode === "recording"}
            aria-label={deck.recordingState.mode === "replaying" ? "Stop playback" : "Play selected recording"}
            title={deck.recordingState.mode === "replaying" ? "Stop playback" : "Play selected recording"}
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
            {deck.recordingState.mode === "replaying" ? (
              <ReplayProgressIcon progress={replayProgress} />
            ) : (
              <ActionIcon kind="play" />
            )}
          </button>
          <button
            className={`${styles.actionButton} ${styles.iconButton}`}
            type="button"
            disabled={busy}
            aria-label="Upload recording"
            title="Upload recording"
            onClick={triggerUpload}
          >
            <ActionIcon kind="upload" />
          </button>
        </div>
        <div className={styles.statusCard} data-mode={deck.recordingState.mode}>
          <RecordingStatusIcon mode={deck.recordingState.mode} />
          <div className={styles.statusText}>
            <strong>{modeLabel}</strong>
            {deck.recordingState.mode === "recording" ? (
              <span>{deck.recordingState.event_count} events captured</span>
            ) : deck.recordingState.mode === "replaying" ? (
              <span>{deck.recordingState.active_name ?? "Playback active"}</span>
            ) : null}
          </div>
        </div>
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
              const isActiveReplay = deck.recordingState.mode === "replaying" && deck.recordingState.replaying_id === item.id;
              return (
                <div
                  key={item.id}
                  className={styles.listItem}
                  data-selected={isSelected}
                  role="button"
                  tabIndex={0}
                  onClick={() => {
                    if (isEditorOpen) {
                      return;
                    }
                    setSelectedId(item.id);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      if (isEditorOpen) {
                        return;
                      }
                      setSelectedId(item.id);
                    }
                  }}
                >
                  <div className={styles.itemTop}>
                    <strong>{item.name}</strong>
                    <div className={styles.itemActions}>
                      <span>{formatDuration(item.duration_ms)}</span>
                      <button
                        className={`${styles.inlineButton} ${styles.iconAction}`}
                        type="button"
                        disabled={
                          busy ||
                          isEditorOpen ||
                          deck.recordingState.mode === "recording" ||
                          (deck.recordingState.mode === "replaying" && !isActiveReplay)
                        }
                        aria-label={isActiveReplay ? `Stop playback for ${item.name}` : `Play ${item.name}`}
                        title={isActiveReplay ? "Stop playback" : "Play recording"}
                        onClick={async (event) => {
                          event.stopPropagation();
                          setSelectedId(item.id);
                          setBusy(true);
                          try {
                            if (isActiveReplay) {
                              await deck.stopRecordingPlayback();
                            } else {
                              await deck.playRecording(item.id);
                            }
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        {isActiveReplay ? (
                          <ReplayProgressIcon progress={replayProgress} />
                        ) : (
                          <ActionIcon kind="play" />
                        )}
                      </button>
                    </div>
                  </div>
                  <div className={styles.itemMeta}>
                    <span>{item.event_count} events</span>
                    <span>{formatTimestamp(item.updated_at)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className={styles.detailPane}>
          <div className={styles.sectionHeader}>
            <span>{isEditorOpen ? "Editor" : "Details"}</span>
            <span>{selected ? selected.filename : "No selection"}</span>
          </div>
          {selected ? (
            <div className={styles.detailCard}>
              {isEditorOpen ? (
                <>
                  <div className={styles.editorMeta}>
                    <span>{selected.filename}</span>
                    <span>{editorDirty ? "Modified" : "Saved"}</span>
                  </div>
                  <textarea
                    className={styles.editorText}
                    value={editorDraft}
                    spellCheck={false}
                    onChange={(event) => setEditorDraft(event.target.value)}
                  />
                  <div className={styles.editorActions}>
                    <button
                      className={`${styles.inlineButton} ${styles.iconAction}`}
                      type="button"
                      onClick={() => {
                        void saveEditor();
                      }}
                      disabled={busy}
                      aria-label="Save file changes"
                      title="Save file changes"
                    >
                      <ActionIcon kind="save" />
                    </button>
                    <button
                      className={`${styles.inlineButton} ${styles.iconAction}`}
                      type="button"
                      onClick={cancelEditorChanges}
                      disabled={busy || !editorDirty}
                      aria-label="Revert file changes"
                      title="Revert file changes"
                    >
                      <ActionIcon kind="cancel" />
                    </button>
                    <button
                      className={`${styles.inlineButton} ${styles.iconAction}`}
                      type="button"
                      onClick={() => {
                        if (editorDirty) {
                          setCloseEditorConfirmOpen(true);
                        } else {
                          closeEditor();
                        }
                      }}
                      disabled={busy}
                      aria-label="Close file editor"
                      title="Close file editor"
                    >
                      <ActionIcon kind="close" />
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className={styles.detailTable}>
                    <div className={styles.detailRow}>
                      <span>Name</span>
                      {renamingId === selected.id ? (
                        <div className={styles.nameEditor}>
                          <input
                            className={styles.renameInput}
                            value={renameDraft}
                            onChange={(event) => setRenameDraft(event.target.value)}
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
                          <button
                            className={`${styles.inlineButton} ${styles.iconAction}`}
                            type="button"
                            onClick={() => {
                              void commitRename();
                            }}
                            disabled={busy || renameDraft.trim().length === 0}
                            aria-label="Save recording name"
                            title="Save recording name"
                          >
                            <ActionIcon kind="save" />
                          </button>
                          <button
                            className={`${styles.inlineButton} ${styles.iconAction}`}
                            type="button"
                            onClick={() => {
                              setRenamingId(null);
                              setRenameDraft("");
                            }}
                            disabled={busy}
                            aria-label="Cancel name edit"
                            title="Cancel name edit"
                          >
                            <ActionIcon kind="cancel" />
                          </button>
                        </div>
                      ) : (
                        <div className={styles.nameValue}>
                          <strong>{selected.name}</strong>
                          <button
                            className={`${styles.inlineButton} ${styles.iconAction} ${styles.nameEditButton}`}
                            type="button"
                            disabled={busy || deck.recordingState.mode !== "idle"}
                            onClick={() => beginRename(selected)}
                            aria-label="Edit recording name"
                            title="Edit recording name"
                          >
                            <ActionIcon kind="rename" />
                          </button>
                        </div>
                      )}
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
                  </div>
                  <div className={styles.detailActions}>
                    <button
                      className={`${styles.inlineButton} ${styles.iconAction}`}
                      type="button"
                      disabled={busy || deck.recordingState.mode !== "idle"}
                      onClick={() => {
                        void beginEdit(selected);
                      }}
                      aria-label="Edit recording file"
                      title="Edit recording file"
                    >
                      <ActionIcon kind="edit" />
                    </button>
                    <a
                      className={`${styles.inlineButton} ${styles.iconAction}`}
                      href={deck.recordingDownloadUrl(selected.id)}
                      download={selected.filename}
                      aria-label="Download recording"
                      title="Download recording"
                    >
                      <ActionIcon kind="download" />
                    </a>
                    <button
                      className={`${styles.inlineButton} ${styles.iconAction} ${styles.deleteButton}`}
                      type="button"
                      disabled={busy || deck.recordingState.mode !== "idle"}
                      onClick={() => onRequestDelete(selected)}
                      aria-label="Delete recording"
                      title="Delete recording"
                    >
                      <ActionIcon kind="delete" />
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className={styles.emptyDetail}>Select a recording to inspect or replay it.</div>
          )}
        </div>
      </div>
      <ConfirmDialog
        open={closeEditorConfirmOpen}
        title="Close Editor"
        message="Save changes before closing the editor?"
        confirmLabel="Save"
        cancelLabel="Discard"
        busy={busy}
        onConfirm={() => {
          void saveEditor().then((saved) => {
            if (saved) {
              closeEditor();
            }
          });
        }}
        onCancel={closeEditor}
      />
    </div>
  );
}
