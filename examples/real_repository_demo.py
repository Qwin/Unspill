#!/usr/bin/env python3
"""Clone octocat/Hello-World and verify local-only recovery. Requires network."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SOURCE = "https://github.com/octocat/Hello-World.git"


def exercise(project: Path, backups: Path, binary: Path | None = None) -> dict:
    """Only call with the disposable clone created by this demonstration."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(UNSPILL_HOME=str(backups), PYTHONPATH=str(Path(__file__).resolve().parents[1]),
               GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="Unspill Demo", GIT_AUTHOR_EMAIL="demo@example.invalid",
               GIT_COMMITTER_NAME="Unspill Demo", GIT_COMMITTER_EMAIL="demo@example.invalid")

    def run(*args):
        return subprocess.run(args, cwd=project, env=env, capture_output=True, check=True).stdout

    def unspill(*args):
        launcher = [str(binary)] if binary else [sys.executable, "-m", "unspill"]
        return run(*launcher, *args)

    run("git", "config", "core.autocrlf", "false")
    original_head = run("git", "rev-parse", "HEAD").decode().strip()
    original_remote = run("git", "remote", "get-url", "origin")
    readme = project / "README"
    original = readme.read_bytes()
    unspill("init")
    readme.write_bytes(original + b"\nStaged demo change\n")
    run("git", "add", "README")
    staged = run("git", "show", ":README")
    readme.write_bytes(original + b"\nUnstaged demo change\n")
    unstaged = readme.read_bytes()
    before_status = run("git", "status", "--porcelain")
    unspill("git", "reset", "--hard")
    assert readme.read_bytes() == original
    unspill("undo")
    assert readme.read_bytes() == unstaged
    assert run("git", "show", ":README") == staged
    assert run("git", "status", "--porcelain") == before_status

    (project / "scratch.bin").write_bytes(bytes(range(256)))
    (project / "ignored-demo.txt").write_text("fake ignored work", encoding="utf-8")
    with (project / ".git/info/exclude").open("a", encoding="utf-8") as stream:
        stream.write("\nignored-demo.txt\n")
    unspill("git", "clean", "-fdx")
    assert not (project / "scratch.bin").exists()
    assert not (project / "ignored-demo.txt").exists()
    unspill("undo")
    assert (project / "scratch.bin").read_bytes() == bytes(range(256))
    assert (project / "ignored-demo.txt").read_text() == "fake ignored work"

    unspill("git", "stash", "push", "-u", "-m", "demo stash")
    stash = run("git", "stash", "list")
    unspill("git", "stash", "clear")
    assert not run("git", "stash", "list")
    unspill("undo")
    assert run("git", "stash", "list") == stash

    run("git", "switch", "-c", "unspill-demo-local-only")
    (project / "demo-commit.txt").write_text("local commit", encoding="utf-8")
    run("git", "add", "demo-commit.txt")
    run("git", "commit", "-m", "Temporary local Unspill recovery test")
    local_head = run("git", "rev-parse", "HEAD")
    unspill("git", "reset", "--hard", "HEAD~1")
    unspill("undo")
    assert run("git", "rev-parse", "HEAD") == local_head
    assert (project / "demo-commit.txt").read_text() == "local commit"

    before = json.loads(unspill("timeline", "--json"))
    unspill("restore", before[0]["id"])
    after = json.loads(unspill("timeline", "--json"))
    assert {s["id"] for s in before} < {s["id"] for s in after}
    assert run("git", "rev-parse", "HEAD").decode().strip() == original_head
    assert run("git", "remote", "get-url", "origin") == original_remote
    assert not run("git", "status", "--porcelain")
    assert readme.read_bytes() == original
    verification = unspill("verify").decode().strip()
    return {"source": SOURCE, "original_commit": original_head,
            "checks": ["staged and unstaged reset recovery", "untracked binary and ignored file recovery",
                       "stash stack recovery", "local commit recovery", "history retained after time travel",
                       "original clean checkout and remote restored"],
            "snapshots": len(after), "verification": verification, "result": "PASS"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, help="New directory for the clone and backups")
    parser.add_argument("--unspill", type=Path, help="Test a standalone executable")
    args = parser.parse_args()
    if args.directory:
        base = args.directory.resolve()
        base.mkdir(parents=True, exist_ok=False)
    else:
        base = Path(tempfile.mkdtemp(prefix="unspill-real-demo-")).resolve()
    subprocess.run(["git", "clone", SOURCE, str(base / "project")], check=True)
    report = exercise(base / "project", base / "backups", args.unspill.resolve() if args.unspill else None)
    (base / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Clone, backups, and report retained at: {base}")


if __name__ == "__main__":
    main()
