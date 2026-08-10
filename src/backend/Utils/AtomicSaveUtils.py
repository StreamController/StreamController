"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import os
import json
import tempfile
from contextlib import contextmanager


@contextmanager
def atomic_write(path: str, mode: str = "w", **open_kwargs):
    """
    Context manager that yields a writable file handle for a temp file
    next to `path`, then atomically replaces `path` with it on success.

    On any exception raised while writing, the temp file is discarded
    and `path` is left untouched - so a crash mid-write (SIGKILL, OOM
    killer, power loss, ...) can never leave a truncated file behind.
    """
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=f".{os.path.basename(path)}.", suffix=".tmp")
    os.close(fd)

    try:
        with open(tmp_path, mode, **open_kwargs) as f:
            yield f
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def atomic_save_json(path: str, data, indent: int | None = 4) -> None:
    with atomic_write(path, "w") as f:
        json.dump(data, f, indent=indent)
