"""Snapshot and restoration orchestration for ordinary, self-contained repos."""

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile
import time
import uuid

from .storage import BGitError, Store, atomic_json, read_json, sync_dir
from .platform import default_home, sync_file, windows_path_is_safe


PROTECTED = frozenset({
    "add", "am", "apply", "branch", "checkout", "cherry-pick", "clean",
    "commit", "fetch", "gc", "merge", "mv", "pull", "rebase", "reset",
    "restore", "revert", "rm", "stash", "switch", "tag",
})
READ_ONLY = frozenset({"diff", "log", "show", "status"})


def reject_git_environment() -> None:
    unsafe = {
        "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
    }
    if found := sorted(unsafe.intersection(os.environ)):
        raise BGitError("Unset Git repository/config overrides: " + ", ".join(found))


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    reject_git_environment()
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )


def discover(path: Path) -> Path:
    result = git(path, "rev-parse", "--show-toplevel")
    if result.returncode:
        raise BGitError("Not a Git working repository. Run git init first, or use --repo PATH for recovery.")
    return Path(os.fsdecode(result.stdout).strip()).resolve()


def record_id(after: int = 0) -> str:
    return f"{max(time.time_ns(), after + 1):020d}-{uuid.uuid4().hex[:12]}"


def remove_tree(root: Path) -> None:
    """Remove a captured tree even when its directories are read-only."""
    for directory, children, files in os.walk(root, followlinks=False):
        os.chmod(directory, 0o700)
        if os.name == "nt":
            for filename in files:
                os.chmod(Path(directory) / filename, 0o600)
    shutil.rmtree(root)


def fingerprint(info: os.stat_result) -> tuple:
    return (info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
            info.st_ino, info.st_dev)


def inventory(root: Path) -> dict:
    """Do not follow symlinks, cross mounts, or silently omit unreadable paths."""
    result = {}
    device = root.stat().st_dev

    def walk(directory: Path):
        for path in sorted(directory.iterdir()):
            relative = path.relative_to(root).as_posix()
            info = path.lstat()
            if os.name == "nt" and getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise BGitError(f"Windows reparse points (including junctions/symlinks) are unsupported: {relative}")
            if info.st_dev != device:
                raise BGitError(f"Mounted filesystems are unsupported: {relative}")
            if path.name == ".git" and relative != ".git":
                raise BGitError(f"Nested repositories/submodules are unsupported: {relative}")
            if relative.startswith(".git/") and path.name.endswith(".lock"):
                raise BGitError(f"Git lock present; finish the Git operation first: {relative}")
            if stat.S_ISLNK(info.st_mode):
                if relative == ".git" or relative.startswith(".git/"):
                    raise BGitError("Symlinks inside Git metadata are unsupported.")
            elif not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                raise BGitError(f"Special files (sockets/devices/FIFOs) are unsupported: {relative}")
            result[relative] = fingerprint(info)
            if stat.S_ISDIR(info.st_mode):
                walk(path)

    walk(root)
    return result


class Repository:
    def __init__(self, root: Path, home: Path | None = None):
        self.root = root.resolve()
        base = home or Path(os.environ.get("BGIT_HOME", str(default_home()))).expanduser()
        base = base.resolve()
        if base == self.root or base.is_relative_to(self.root) or self.root.is_relative_to(base):
            raise BGitError("BGIT_HOME must be outside the repository, and cannot contain it.")
        identity = hashlib.sha256(os.fsencode(str(self.root))).hexdigest()
        self.store = Store(base / "repositories" / identity)
        self.pending = self.store.path / "pending.json"

    def initialize(self) -> dict:
        self.validate_repository()
        self.store.create()
        with self.store.lock():
            if (self.store.path / "repository.json").exists():
                raise BGitError("BGit is already initialized here.")
            snapshot = self.snapshot("Initial snapshot", kind="initial")
            atomic_json(self.store.path / "repository.json", {"version": 1, "root": str(self.root)}, immutable=True)
            return snapshot

    def require_initialized(self) -> None:
        metadata = read_json(self.store.path / "repository.json")
        if metadata.get("version") != 1 or metadata.get("root") != str(self.root):
            raise BGitError("Backup store does not match this repository.")

    def require_idle(self) -> None:
        if self.pending.exists():
            raise BGitError("An interrupted restore is pending. Use bgit resume (or resume --rollback).")

    def validate_repository(self) -> None:
        reject_git_environment()
        metadata = self.root / ".git"
        if not metadata.is_dir() or metadata.is_symlink():
            raise BGitError("Only ordinary repositories with a real .git directory are supported.")
        for relative in ("commondir", "objects/info/alternates"):
            if (metadata / relative).exists():
                raise BGitError("Shared Git directories/object stores are unsupported.")
        if (metadata / "worktrees").exists() and any((metadata / "worktrees").iterdir()):
            raise BGitError("Repositories with linked worktrees are unsupported.")
        for key in ("core.worktree", "extensions.partialclone", "core.sparsecheckout"):
            result = git(self.root, "config", "--get", key)
            if result.returncode == 0 and result.stdout.strip().lower() not in (b"false", b"0"):
                raise BGitError(f"Unsupported repository setting: {key}")
        if git(self.root, "config", "--get-regexp", r"remote\..*\.promisor").returncode == 0:
            raise BGitError("Partial clones are unsupported.")
        result = git(self.root, "ls-files", "--stage", "-z")
        if result.returncode:
            raise BGitError("Cannot read the Git index.")
        if any(entry.startswith(b"160000 ") for entry in result.stdout.split(b"\0")):
            raise BGitError("Submodules are unsupported.")

    def snapshot(self, label: str, *, kind: str = "manual", source: str | None = None) -> dict:
        self.require_idle()
        self.validate_repository()
        before = inventory(self.root)
        entries = {}
        for relative, signature in before.items():
            path = self.root / relative
            mode = signature[0]
            entry = {"mode": stat.S_IMODE(mode)}
            if stat.S_ISDIR(mode):
                entry["type"] = "directory"
            elif stat.S_ISLNK(mode):
                entry.update(type="symlink", target=os.readlink(path))
            else:
                # O_NOFOLLOW closes the most common symlink substitution race.
                fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
                with os.fdopen(fd, "rb") as stream:
                    if fingerprint(os.fstat(stream.fileno())) != signature:
                        raise BGitError(f"File changed during snapshot: {relative}")
                    entry.update(type="file", object=self.store.put(stream), size=signature[1])
            if fingerprint(path.lstat()) != signature:
                raise BGitError(f"File changed during snapshot: {relative}")
            entries[relative] = entry
        if before != inventory(self.root):
            raise BGitError("Repository changed during snapshot. Pause other writers and retry.")
        previous = max((path.stem for path in self.store.snapshots.glob("*.json")), default="0-")
        snapshot = {
            "version": 1, "id": record_id(int(previous.split("-")[0])),
            "created": datetime.now(timezone.utc).isoformat(),
            "label": label, "kind": kind, "source": source, "entries": entries,
        }
        atomic_json(self.store.snapshots / (snapshot["id"] + ".json"), snapshot, immutable=True)
        return snapshot

    def timeline(self) -> list[dict]:
        return [self.load(path.stem) for path in sorted(self.store.snapshots.glob("*.json"))]

    def load(self, selector: str) -> dict:
        if not selector or any(c not in "0123456789abcdef-" for c in selector):
            raise BGitError("Use a snapshot ID or unique ID prefix from bgit timeline.")
        matches = list(self.store.snapshots.glob(selector + "*.json"))
        if len(matches) != 1:
            raise BGitError(f"Snapshot ID matched {len(matches)} records; use a unique ID.")
        value = read_json(matches[0])
        if value.get("version") != 1 or value.get("id") != matches[0].stem:
            raise BGitError("Unsupported or invalid snapshot manifest.")
        entries = value.get("entries")
        if not isinstance(entries, dict) or not isinstance(entries.get(".git"), dict) or entries[".git"].get("type") != "directory":
            raise BGitError("Snapshot is missing Git metadata.")
        if any(not isinstance(value.get(key), str) for key in ("created", "label", "kind")):
            raise BGitError("Invalid snapshot metadata.")
        for name, entry in entries.items():
            path = PurePosixPath(name)
            if not name or name == "." or path.is_absolute() or ".." in path.parts or str(path) != name or "\0" in name:
                raise BGitError("Unsafe path in snapshot.")
            if not isinstance(entry, dict) or entry.get("type") not in {"file", "directory", "symlink"}:
                raise BGitError("Invalid snapshot entry.")
            if os.name == "nt" and (not windows_path_is_safe(name) or entry["type"] == "symlink"):
                raise BGitError("Snapshot contains a path unsupported on Windows.")
            if type(entry.get("mode")) is not int or not 0 <= entry["mode"] <= 0o7777:
                raise BGitError("Invalid file mode.")
            if entry["type"] == "file":
                self.store.object_path(entry.get("object"))
                if type(entry.get("size")) is not int or entry["size"] < 0:
                    raise BGitError("Invalid file size.")
            if entry["type"] == "symlink":
                if name.startswith(".git/") or not isinstance(entry.get("target"), str) or not entry["target"] or "\0" in entry["target"]:
                    raise BGitError("Invalid symlink.")
            for parent in path.parents:
                if str(parent) != "." and entries.get(str(parent), {}).get("type") != "directory":
                    raise BGitError("Snapshot path has a missing or non-directory parent.")
        return value

    def materialize(self, snapshot: dict, destination: Path, selected: str | None = None) -> None:
        entries = snapshot["entries"]
        if selected is not None:
            if selected not in entries or selected == ".git" or selected.startswith(".git/"):
                raise BGitError("Select an existing workspace file or directory, not Git metadata.")
            entries = {name: entry for name, entry in entries.items()
                       if name == selected or name.startswith(selected + "/")}
        for name, entry in sorted(entries.items(), key=lambda pair: (pair[0].count("/"), pair[0])):
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if entry["type"] == "directory":
                path.mkdir(exist_ok=True)
            elif entry["type"] == "symlink":
                path.symlink_to(entry["target"])
            else:
                with path.open("xb") as output:
                    self.store.extract(entry["object"], output)
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(path, entry["mode"] & 0o777)
        # Set directory modes last so read-only directories can be populated.
        for name, entry in sorted(entries.items(), reverse=True):
            if entry["type"] == "directory":
                sync_dir(destination / name)
                os.chmod(destination / name, entry["mode"] & 0o777)
        sync_dir(destination)

    def recover(self, selector: str, destination: Path, selected: str | None = None) -> None:
        snapshot = self.load(selector)
        destination = destination.absolute()
        resolved = destination.resolve()
        if resolved.is_relative_to(self.root) or resolved.is_relative_to(self.store.path):
            raise BGitError("Recovery destination must be outside the repository and its backup store.")
        if destination.exists() or destination.is_symlink():
            raise BGitError("Recovery destination must not already exist.")
        destination.mkdir(parents=True, mode=0o700)
        try:
            self.materialize(snapshot, destination, selected)
        except BaseException:
            remove_tree(destination)
            raise

    def restore(self, selector: str) -> dict:
        self.require_idle()
        snapshot = self.load(selector)
        # Validate and stage all content before creating a recovery transaction.
        with tempfile.TemporaryDirectory(dir=self.store.path, prefix="restore-") as name:
            self.materialize(snapshot, Path(name))
            before = self.snapshot(f"Before restoring {snapshot['id']}", kind="before-restore", source=snapshot["id"])
            journal = {"target": snapshot["id"], "rollback": before["id"]}
            atomic_json(self.pending, journal)
            self._replace_tree(Path(name))
            self._finish_restore(journal)
        return before

    def resume(self, rollback: bool = False) -> None:
        journal = read_json(self.pending)
        target = journal["rollback"] if rollback else journal["target"]
        snapshot = self.load(target)
        with tempfile.TemporaryDirectory(dir=self.store.path, prefix="restore-") as name:
            self.materialize(snapshot, Path(name))
            self._replace_tree(Path(name))
            self._finish_restore({**journal, "restored": target})

    def _replace_tree(self, staged: Path) -> None:
        # This is resumable, not an atomic filesystem-wide transaction.
        inventory(self.root)
        for path in self.root.iterdir():
            if path.is_symlink() or not path.is_dir():
                if os.name == "nt":
                    os.chmod(path, 0o600)
                path.unlink()
            else:
                remove_tree(path)
        for path in staged.iterdir():
            # Copy supports stores on a different filesystem. The journal stays
            # present until every file and directory has been synced.
            target = self.root / path.name
            if path.is_symlink():
                target.symlink_to(os.readlink(path))
            elif path.is_dir():
                shutil.copytree(path, target, symlinks=True)
            else:
                shutil.copy2(path, target)
        for name, signature in inventory(self.root).items():
            if stat.S_ISREG(signature[0]):
                sync_file(self.root / name)
        for name, signature in sorted(inventory(self.root).items(), reverse=True):
            if stat.S_ISDIR(signature[0]):
                sync_dir(self.root / name)
        sync_dir(self.root)

    def _finish_restore(self, journal: dict) -> None:
        atomic_json(self.store.events / (record_id() + ".json"), {"kind": "restore", **journal}, immutable=True)
        self.pending.unlink()
        sync_dir(self.store.path)

    def undo(self) -> dict:
        candidates = [s for s in self.timeline() if s["kind"] in {"before-command", "before-restore"}]
        if not candidates:
            raise BGitError("Nothing to undo. Make a protected Git operation first.")
        return self.restore(candidates[-1]["id"])

    def run(self, args: list[str], cwd: Path) -> int:
        self.require_idle()
        if not args or args[0] not in PROTECTED | READ_ONLY:
            raise BGitError("Unsupported Git command. Use a supported built-in subcommand; aliases/global Git options are not accepted.")
        self.validate_repository()
        if args[0] in PROTECTED:
            # Do not store arguments, which may contain credentials or commit messages.
            snapshot = self.snapshot(f"Before git {args[0]}", kind="before-command")
            print(f"BGit checkpoint: {snapshot['id']}", flush=True)
        result = subprocess.run(
            ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", *args], cwd=cwd,
        )
        return result.returncode
