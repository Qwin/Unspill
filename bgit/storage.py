"""Durable, content-addressed storage. No expiry or deletion API."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import zlib

from .platform import LockUnavailable, exclusive_lock, sync_dir


class BGitError(Exception):
    """An actionable error suitable for display without a traceback."""


def atomic_json(path: Path, value: dict, *, immutable: bool = False) -> None:
    data = json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2).encode()
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if immutable:
            os.link(temporary, path)  # Fail rather than replace an existing record.
        else:
            os.replace(temporary, path)
        sync_dir(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise BGitError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BGitError(f"Invalid record: {path}")
    return value


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.objects = path / "objects"
        self.snapshots = path / "snapshots"
        self.events = path / "events"

    def create(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path, 0o700)
        for directory in (self.objects, self.snapshots, self.events):
            directory.mkdir(exist_ok=True, mode=0o700)
        sync_dir(self.path)

    @contextmanager
    def lock(self):
        with (self.path / "lock").open("a+b") as stream:
            try:
                with exclusive_lock(stream):
                    yield
            except LockUnavailable as exc:
                raise BGitError("Another BGit operation is running.") from exc

    def object_path(self, digest: str) -> Path:
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise BGitError("Invalid object identifier.")
        return self.objects / digest

    def put(self, stream) -> str:
        digest = hashlib.sha256()
        compressor = zlib.compressobj()
        fd, name = tempfile.mkstemp(dir=self.objects, prefix=".pending-")
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as output:
                while block := stream.read(1024 * 1024):
                    digest.update(block)
                    output.write(compressor.compress(block))
                output.write(compressor.flush())
                output.flush()
                os.fsync(output.fileno())
            key = digest.hexdigest()
            destination = self.object_path(key)
            if destination.exists():
                # Never reuse corrupt content simply because its name matches.
                self.extract(key, None)
            else:
                os.link(temporary, destination)
                sync_dir(self.objects)
            return key
        finally:
            temporary.unlink(missing_ok=True)

    def extract(self, digest: str, output) -> None:
        checksum = hashlib.sha256()
        decoder = zlib.decompressobj()
        try:
            with self.object_path(digest).open("rb") as stream:
                while block := stream.read(64 * 1024):
                    while block:
                        data = decoder.decompress(block, 1024 * 1024)
                        block = decoder.unconsumed_tail
                        checksum.update(data)
                        if output is not None:
                            output.write(data)
                if not decoder.eof or decoder.unused_data:
                    raise BGitError(f"Incomplete or trailing object data: {digest}")
        except (OSError, zlib.error) as exc:
            raise BGitError(f"Cannot read backup object {digest}: {exc}") from exc
        if checksum.hexdigest() != digest:
            raise BGitError(f"Backup checksum mismatch: {digest}")
