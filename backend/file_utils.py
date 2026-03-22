"""Atomic file write utility to prevent corruption from concurrent writes."""
import json
import os
import tempfile
from pathlib import Path


def atomic_json_write(filepath, data):
    """Write JSON data to a file atomically.

    Writes to a temporary file in the same directory, then renames it
    to the target path. os.rename is atomic on the same filesystem.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=filepath.parent,
        prefix=filepath.stem + "_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.rename(tmp_path, filepath)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
