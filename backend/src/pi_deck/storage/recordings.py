"""Disk storage for user recordings."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pi_deck.models.recordings import RecordingFile, RecordingLibraryOut, RecordingSummary


def default_recordings_dir() -> Path:
    env = os.environ.get("PI_DECK_RECORDINGS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".local" / "share" / "pi-deck" / "recordings"


def _safe_stem(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-.")
    return stem or "recording"


class RecordingStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        preferred = (base_dir or default_recordings_dir()).resolve()
        try:
            preferred.mkdir(parents=True, exist_ok=True)
            self._base_dir = preferred
        except PermissionError:
            fallback = (Path(tempfile.gettempdir()) / "pi-deck-recordings").resolve()
            fallback.mkdir(parents=True, exist_ok=True)
            self._base_dir = fallback

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def _path_for(self, recording_id: str) -> Path:
        path = (self._base_dir / recording_id).resolve()
        if path.parent != self._base_dir or path.suffix != ".json":
            raise FileNotFoundError(recording_id)
        return path

    def read(self, recording_id: str) -> RecordingFile:
        path = self._path_for(recording_id)
        return RecordingFile.model_validate_json(path.read_text())

    def list(self) -> RecordingLibraryOut:
        items: list[RecordingSummary] = []
        for path in sorted(self._base_dir.glob("*.json"), reverse=True):
            try:
                recording = RecordingFile.model_validate_json(path.read_text())
            except Exception:
                continue
            items.append(
                RecordingSummary(
                    id=path.name,
                    filename=path.name,
                    name=recording.name,
                    created_at=recording.created_at,
                    updated_at=recording.updated_at,
                    event_count=len(recording.events),
                    duration_ms=recording.duration_ms,
                    size_bytes=path.stat().st_size,
                ),
            )
        return RecordingLibraryOut(items=items)

    def write_new(self, recording: RecordingFile, *, preferred_stem: str) -> RecordingSummary:
        stem = _safe_stem(preferred_stem)
        path = self._base_dir / f"{stem}.json"
        index = 2
        while path.exists():
            path = self._base_dir / f"{stem}-{index}.json"
            index += 1
        path.write_text(json.dumps(recording.model_dump(mode="json"), indent=2) + "\n")
        return RecordingSummary(
            id=path.name,
            filename=path.name,
            name=recording.name,
            created_at=recording.created_at,
            updated_at=recording.updated_at,
            event_count=len(recording.events),
            duration_ms=recording.duration_ms,
            size_bytes=path.stat().st_size,
        )

    def rename(self, recording_id: str, *, new_name: str) -> RecordingSummary:
        path = self._path_for(recording_id)
        recording = RecordingFile.model_validate_json(path.read_text())
        updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        updated = recording.model_copy(update={"name": new_name, "updated_at": updated_at})
        new_path = self._base_dir / f"{_safe_stem(new_name)}.json"
        index = 2
        while new_path.exists() and new_path != path:
            new_path = self._base_dir / f"{_safe_stem(new_name)}-{index}.json"
            index += 1
        path.unlink()
        new_path.write_text(json.dumps(updated.model_dump(mode="json"), indent=2) + "\n")
        return RecordingSummary(
            id=new_path.name,
            filename=new_path.name,
            name=updated.name,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            event_count=len(updated.events),
            duration_ms=updated.duration_ms,
            size_bytes=new_path.stat().st_size,
        )

    def delete(self, recording_id: str) -> None:
        self._path_for(recording_id).unlink()

    def path_for_download(self, recording_id: str) -> Path:
        return self._path_for(recording_id)
