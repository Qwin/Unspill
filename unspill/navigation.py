"""Human-readable history and read-only comparisons against captured states."""

from datetime import datetime
import difflib
import hashlib
import io
import os
import stat

from .repository import inventory
from .storage import UnspillError, read_json


def safe(value) -> str:
    """Display repository-controlled text without terminal control characters."""
    return "".join(c if c.isprintable() else repr(c)[1:-1] for c in str(value))


def numbered(repo) -> list[dict]:
    outcomes = {}
    for path in sorted(repo.store.events.glob("*.json")):
        event = read_json(path)
        if event.get("kind") == "command":
            outcomes[event.get("snapshot")] = event.get("outcome", "unknown")
    return [{**snapshot, "number": index, "outcome": outcomes.get(snapshot["id"], "unknown" if snapshot["kind"] == "before-command" else None)}
            for index, snapshot in enumerate(repo.timeline(), 1)]


def counts(snapshot: dict) -> dict:
    changes = snapshot.get("context", {}).get("changes", [])
    return {"staged": sum(c["status"][0] not in " ?" for c in changes),
            "unstaged": sum(c["status"][1] not in " ?" for c in changes),
            "untracked": sum(c["status"] == "??" for c in changes)}


def entry_text(snapshot: dict) -> str:
    context = snapshot.get("context", {})
    timestamp = datetime.fromisoformat(snapshot["created"]).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [f"#{snapshot['number']}  {timestamp}  {safe(context.get('branch', '(branch not recorded)'))}",
             f"  {safe(snapshot['label'])}"]
    if context:
        lines.append(f"  Commit: {safe(context.get('subject'))} [{(context.get('commit') or 'unborn')[:8]}]")
        total = counts(snapshot)
        lines.append(f"  Saved: {total['staged']} staged, {total['unstaged']} unstaged, {total['untracked']} untracked; {len(context.get('stashes', []))} stashes")
        for change in context.get("changes", [])[:5]:
            lines.append(f"    {change['status']} {safe(change['path'])}")
        if len(context.get("changes", [])) > 5:
            lines.append("    ... use inspect for all paths")
        for stash in context.get("stashes", [])[:3]:
            lines.append(f"    Stash: {safe(stash)}")
    else:
        lines.append("  Legacy snapshot: branch, commit and change summaries were not recorded.")
    if snapshot.get("outcome"):
        lines.append(f"  Operation outcome: {safe(snapshot['outcome'])}")
    lines.append(f"  Select: @{snapshot['number']}  |  ID: {snapshot['id']}")
    return "\n".join(lines)


def find_records(repo, search: str | None = None, branch: str | None = None) -> list[dict]:
    records = numbered(repo)
    if branch:
        records = [s for s in records if s.get("context", {}).get("branch") == branch]
    if search:
        query = search.casefold()
        records = [s for s in records if query in str((s["label"], s.get("context", {}))).casefold()]
    return records


def workspace(entries):
    return {name: value for name, value in entries.items() if name != ".git" and not name.startswith(".git/")}


def live_entries(repo) -> dict:
    before = inventory(repo.root)
    entries = {}
    for name, signature in before.items():
        path = repo.root / name
        item = {"mode": stat.S_IMODE(signature[0])}
        if stat.S_ISDIR(signature[0]):
            item["type"] = "directory"
        elif stat.S_ISLNK(signature[0]):
            item.update(type="symlink", target=os.readlink(path))
        else:
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            item.update(type="file", object=digest, size=signature[1])
        entries[name] = item
    if before != inventory(repo.root):
        raise UnspillError("Repository changed during preview. Pause other writers and retry.")
    return entries


def preview(repo, snapshot: dict) -> dict:
    current_all = live_entries(repo)
    current = workspace(current_all)
    target = workspace(snapshot["entries"])
    changes = []
    for name in sorted(current.keys() | target.keys()):
        old, new = current.get(name), target.get(name)
        if old != new:
            action = "recover" if old is None else "remove" if new is None else "replace"
            changes.append({"path": name, "action": action, "type": (new or old)["type"]})
    git_changes = [name for name in sorted(current_all.keys() | snapshot["entries"].keys())
                   if (name == ".git" or name.startswith(".git/")) and current_all.get(name) != snapshot["entries"].get(name)]
    return {"changes": changes, "git_metadata_changed": bool(git_changes),
            "index_changed": ".git/index" in git_changes,
            "target_branch": snapshot.get("context", {}).get("branch"),
            "target_commit": snapshot.get("context", {}).get("commit")}


def preview_text(result: dict) -> str:
    lines = ["Restoration preview (current workspace -> selected checkpoint):"]
    for change in result["changes"]:
        lines.append(f"  {change['action'].capitalize():7} {safe(change['path'])} ({change['type']})")
    if not result["changes"]:
        lines.append("  No workspace content or permission changes.")
    if result["git_metadata_changed"]:
        lines.append("  Restore captured Git metadata: refs, stashes, configuration and hooks.")
    if result["index_changed"]:
        lines.append("  Restore captured staging/index state.")
    if result["target_branch"]:
        lines.append(f"  Captured branch: {safe(result['target_branch'])}")
    if result["target_commit"]:
        lines.append(f"  Captured commit: {result['target_commit'][:12]}")
    lines.append("Your current state will be checkpointed before a full restore. Nothing has changed yet.")
    return "\n".join(lines)


def file_history(repo, path: str) -> list[dict]:
    records = numbered(repo)
    previous = object()
    result = []
    found = False
    for snapshot in records:
        entry = workspace(snapshot["entries"]).get(path)
        if entry is not None:
            found = True
        if entry != previous:
            result.append({**snapshot, "file_state": "absent" if entry is None else entry["type"]})
        previous = entry
    if not found:
        raise UnspillError("That path does not appear in any captured workspace.")
    return result


def file_diff(repo, snapshot: dict, path: str) -> str:
    target = workspace(snapshot["entries"]).get(path)
    current = workspace(live_entries(repo)).get(path)
    if target is None and current is None:
        raise UnspillError("File is absent in both the checkpoint and current workspace.")
    if any(entry and entry["type"] != "file" for entry in (current, target)):
        return "This path changes type or is a directory/symlink; inspect the restoration preview."
    if any(entry and entry.get("size", 0) > 1024 * 1024 for entry in (current, target)):
        return "File exceeds the 1 MiB text-diff limit; use recover --to to inspect a separate copy."
    output = io.BytesIO()
    if target:
        repo.store.extract(target["object"], output)
    saved = output.getvalue()
    live = (repo.root / path).read_bytes() if current else b""
    try:
        if b"\0" in saved or b"\0" in live:
            raise UnicodeError
        old_lines = live.decode("utf-8").splitlines(keepends=True)
        new_lines = saved.decode("utf-8").splitlines(keepends=True)
    except UnicodeError:
        return "Binary/non-UTF-8 contents: " + ("unchanged" if live == saved else "different; use recover --to for a separate copy")
    diff = "".join(difflib.unified_diff(old_lines, new_lines, fromfile=f"current/{path}", tofile=f"checkpoint/{path}"))
    # Preserve line breaks but escape terminal controls in arbitrary file content.
    return "\n".join(safe(line) for line in diff.splitlines()) or "No text-content differences."
