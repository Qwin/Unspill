"""Command-line interface; recovery never requires a service or subscription."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .repository import Repository, discover
from .storage import BGitError


def command_parser(command: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=f"bgit {command}")
    if command == "snapshot":
        parser.add_argument("-m", "--message", default="Manual snapshot")
    elif command == "timeline":
        parser.add_argument("--json", action="store_true")
    elif command in {"inspect", "restore", "recover"}:
        parser.add_argument("snapshot")
        if command == "restore":
            parser.add_argument("--dry-run", action="store_true")
        if command == "recover":
            parser.add_argument("--to", required=True, type=Path)
            parser.add_argument("--path", help="Repository-relative file or directory")
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
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="BGit — keep your work recoverable before you commit.",
        epilog="Commands: init, snapshot, timeline, inspect, restore, recover, undo, resume, verify, git. "
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
            if command in {"snapshot", "timeline", "inspect", "restore", "recover", "undo", "resume", "verify"}:
                args = command_parser(command).parse_args(options.arguments)
            if command == "snapshot":
                print(repo.snapshot(args.message)["id"])
            elif command == "timeline":
                records = [summarize(s) for s in repo.timeline()]
                if args.json:
                    print(json.dumps(records, indent=2))
                else:
                    for item in records:
                        print(f"{item['id']}  {item['created']}  {item['label']!r}  ({item['workspace_files']} files)")
                    if repo.pending.exists():
                        print("Interrupted restore pending. Use resume or resume --rollback.")
            elif command == "inspect" or (command == "restore" and args.dry_run):
                print(json.dumps(summarize(repo.load(args.snapshot)), indent=2))
                if command == "restore":
                    print("Would replace the full workspace and .git metadata; a checkpoint would preserve current state.")
            elif command == "restore":
                checkpoint = repo.restore(args.snapshot)
                print(f"Restored. Previous state retained as {checkpoint['id']}")
            elif command == "recover":
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
