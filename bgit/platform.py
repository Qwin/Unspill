"""Small OS-specific primitives; the recovery engine stays platform neutral."""

from contextlib import contextmanager
import os
from pathlib import Path, PureWindowsPath
import stat

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class LockUnavailable(Exception):
    """The advisory lock could not be acquired."""


def default_home() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "BGit"
    return Path.home() / ".local/share/bgit"


@contextmanager
def exclusive_lock(stream):
    try:
        if os.name == "nt":
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, PermissionError) as exc:
        raise LockUnavailable from exc
    try:
        yield
    finally:
        if os.name == "nt":
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(stream, fcntl.LOCK_UN)


def sync_dir(path: Path) -> None:
    # Python cannot portably fsync a directory on Windows. File contents are
    # flushed, but directory-entry power-loss durability is not promised there.
    if os.name == "nt":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def sync_file(path: Path) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if os.name == "nt":
        os.chmod(path, mode | stat.S_IWRITE)
    try:
        with path.open("r+b" if os.name == "nt" else "rb") as stream:
            os.fsync(stream.fileno())
    finally:
        if os.name == "nt":
            os.chmod(path, mode)


def windows_path_is_safe(name: str) -> bool:
    """Reject drive paths, ADS, device names and paths Win32 normalizes."""
    if "\\" in name or PureWindowsPath(name).drive:
        return False
    for part in name.split("/"):
        if part.endswith((" ", ".")) or any(c in '<>:"|?*' or ord(c) < 32 for c in part):
            return False
        stem = part.split(".")[0].upper()
        if stem in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}:
            return False
        if stem in {f"{prefix}{digit}" for prefix in ("COM", "LPT") for digit in "123456789¹²³"}:
            return False
    return True
