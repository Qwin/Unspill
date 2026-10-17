#!/usr/bin/env python3
"""Create a disposable repository, lose work intentionally, and recover it."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, help="New directory to hold the isolated demo")
    parser.add_argument("--unspill", type=Path, help="Test a standalone Unspill executable instead of the source module")
    args = parser.parse_args()
    if args.directory:
        base = args.directory.resolve()
        base.mkdir(parents=True, exist_ok=False)
    else:
        base = Path(tempfile.mkdtemp(prefix="unspill-demo-")).resolve()
    project = base / "project"
    project.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        PYTHONPATH=str(Path(__file__).resolve().parents[1]),
        UNSPILL_HOME=str(base / "backups"), GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="Unspill Demo",
        GIT_AUTHOR_EMAIL="demo@example.invalid", GIT_COMMITTER_NAME="Unspill Demo",
        GIT_COMMITTER_EMAIL="demo@example.invalid", GIT_TERMINAL_PROMPT="0",
    )

    def command(*args, quiet=False):
        result = subprocess.run(args, cwd=project, env=env, check=True,
                                capture_output=True, text=True)
        if not quiet:
            print(result.stdout, end="", flush=True)
        return result.stdout

    def unspill(*args, quiet=False):
        launcher = [str(parsed_binary)] if parsed_binary else [sys.executable, "-m", "unspill"]
        return command(*launcher, *args, quiet=quiet)

    parsed_binary = args.unspill.resolve() if args.unspill else None
    print(f"Demo files and permanent history: {base}", flush=True)
    command("git", "init", "-b", "main", quiet=True)
    command("git", "config", "core.autocrlf", "false")
    tracked = project / "story.txt"
    tracked.write_text("committed\n")
    (project / ".gitignore").write_text("local.env\n")
    command("git", "add", ".")
    command("git", "commit", "-m", "Start demo", quiet=True)
    unspill("init")

    tracked.write_text("staged version\n")
    command("git", "add", "story.txt")
    tracked.write_text("unstaged version\n")
    unspill("git", "reset", "--hard")
    assert tracked.read_text() == "committed\n"
    unspill("undo")
    assert tracked.read_text() == "unstaged version\n"
    assert command("git", "show", ":story.txt", quiet=True) == "staged version\n"
    print("PASS: hard reset recovered staged and unstaged versions", flush=True)

    (project / "scratch.txt").write_text("untracked work")
    (project / "local.env").write_text("DEMO_ONLY=not-a-secret\n")
    unspill("git", "clean", "-fdx")
    assert not (project / "scratch.txt").exists()
    assert not (project / "local.env").exists()
    unspill("undo")
    assert (project / "scratch.txt").read_text() == "untracked work"
    assert (project / "local.env").exists()
    print("PASS: clean recovered untracked and ignored files", flush=True)

    unspill("git", "stash", "push", "-u", "-m", "Work worth keeping")
    stash = command("git", "stash", "list", quiet=True)
    unspill("git", "stash", "clear")
    assert not command("git", "stash", "list", quiet=True)
    unspill("undo")
    assert command("git", "stash", "list", quiet=True) == stash
    print("PASS: stash clear recovered the stash", flush=True)

    before = json.loads(unspill("timeline", "--json", quiet=True))
    unspill("restore", before[0]["id"])
    after = json.loads(unspill("timeline", "--json", quiet=True))
    assert {s["id"] for s in before} < {s["id"] for s in after}
    print("PASS: restoring the past retained later history", flush=True)
    unspill("verify")
    print(f"Explore: UNSPILL_HOME={base / 'backups'} unspill --repo {project} timeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
