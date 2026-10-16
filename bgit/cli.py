"""Command-line interface; recovery never requires a service or subscription."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .repository import Repository, discover
from .storage import BGitError
from .navigation import entry_text, file_diff, file_history, find_records, preview, preview_text
from .wizard import recover_interactively


def command_parser(command: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=f"bgit {command}")
    if command == "snapshot":
        parser.add_argument("-m", "--message", default="Manual snapshot")
    elif command == "timeline":
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--search")
        parser.add_argument("--branch")
    elif command == "history":
        parser.add_argument("path")
        parser.add_argument("--json", action="store_true")
    elif command in {"inspect", "restore", "recover", "diff"}:
        parser.add_argument("snapshot", nargs="?" if command == "recover" else None)
        if command == "restore":
            parser.add_argument("--dry-run", action="store_true")
        if command == "recover":
            parser.add_argument("--to", type=Path)
            parser.add_argument("--path", help="Repository-relative file or directory")
        if command == "diff":
            parser.add_argument("--path", required=True)
    elif command == "resume":
        parser.add_argument("--rollback", action="store_true")
    return parser


def summarize(snapshot: dict) -> dict:
    workspace = {p: e for p, e in snapshot["entries"].items()
                 if p != ".git" and not p.startswith(".git/")}
    return {key: snapshot[key] for key in ("id", "created", "label", "kind")} | {
        "workspace_files": sum(e["type"] != "directory" for e in workspace.values()),
        "workspace_bytes": sum(e.get("size", 0) for e in workspace.values()),
        "paths": sorted(workspace),
        "context": snapshot.get("context"), "number": snapshot.get("number"),
        "outcome": snapshot.get("outcome"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="BGit — keep your work recoverable before you commit.",
        epilog="Commands: init, snapshot, timeline, history, inspect, diff, restore, recover, undo, resume, verify, git. "
               "Example: bgit git reset --hard HEAD~1",
    )
    parser.add_argument("--version", action="version", version=f"BGit {__version__}")
    parser.add_argument("--repo", type=Path, help="Repository root (also works during interrupted recovery)")
    parser.add_argument("command", nargs="?")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    options = parser.parse_args(argv)
    if options.command is None:
        parser.print_help()
        return 0
    command = options.command
    try:
        cwd = options.repo.resolve() if options.repo else Path.cwd()
        root = options.repo.resolve() if options.repo else discover(cwd)
        repo = Repository(root)
        if command == "init":
            command_parser(command).parse_args(options.arguments)
            snapshot = repo.initialize()
            print(f"BGit initialized. Snapshot: {snapshot['id']}\nStore: {repo.store.path}")
            print("All workspace files, including ignored files, are captured locally. No automatic expiry.")
            return 0
        repo.require_initialized()
        with repo.store.lock():
            if command in {"snapshot", "timeline", "history", "inspect", "diff", "restore", "recover", "undo", "resume", "verify"}:
                args = command_parser(command).parse_args(options.arguments)
            if command == "snapshot":
                print(repo.snapshot(args.message)["id"])
            elif command == "timeline":
                records = find_records(repo, args.search, args.branch)
                if args.json:
                    print(json.dumps([summarize(s) for s in records], indent=2))
                else:
                    for item in reversed(records):
                        print(entry_text(item) + "\n")
                    if not records:
                        print("No matching checkpoints.")
                    if repo.pending.exists():
                        print("Interrupted restore pending. Use resume or resume --rollback.")
            elif command == "history":
                records = file_history(repo, args.path)
                if args.json:
                    print(json.dumps([{**summarize(s), "file_state": s["file_state"]} for s in records], indent=2))
                else:
                    for item in reversed(records):
                        print(entry_text(item) + f"\n  Captured path state: {item['file_state']}\n")
            elif command == "diff":
                print(file_diff(repo, repo.load(args.snapshot), args.path))
            elif command == "inspect":
                print(json.dumps(summarize(repo.load(args.snapshot)), indent=2))
            elif command == "restore" and args.dry_run:
                print(preview_text(preview(repo, repo.load(args.snapshot))))
            elif command == "restore":
                checkpoint = repo.restore(args.snapshot)
                print(f"Restored. Previous state retained as {checkpoint['id']}")
            elif command == "recover":
                if args.snapshot is None and args.to is None and args.path is None:
                    recover_interactively(repo)
                elif args.snapshot is None or args.to is None:
                    raise BGitError("For export, provide both a snapshot and --to DIRECTORY; use recover alone for the picker.")
                else:
                    repo.recover(args.snapshot, args.to, args.path)
                    print(f"Recovered to {args.to.absolute()}")
            elif command == "undo":
                checkpoint = repo.undo()
                print(f"Restored latest pre-operation state. Undo this restore with {checkpoint['id']}")
            elif command == "resume":
                repo.resume(args.rollback)
                print("Recovery transaction completed.")
            elif command == "verify":
                snapshots = repo.timeline()
                objects = {e["object"] for s in snapshots for e in s["entries"].values() if e["type"] == "file"}
                for digest in sorted(objects):
                    repo.store.extract(digest, None)
                print(f"Verified {len(snapshots)} snapshots and {len(objects)} unique objects.")
            else:
                return repo.run(options.arguments if command == "git" else [command, *options.arguments], cwd)
        return 0
    except (BGitError, OSError) as exc:
        print(f"bgit: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("bgit: interrupted; check timeline. If a restore is pending, use --repo PATH resume.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
