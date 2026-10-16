"""Hermetic repositories: tests never read user Git config or use the network."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from bgit.repository import Repository


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "project"
        self.root.mkdir()
        clean_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        clean_env.update(
            GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
            GIT_AUTHOR_NAME="BGit Test", GIT_AUTHOR_EMAIL="test@example.invalid",
            GIT_COMMITTER_NAME="BGit Test", GIT_COMMITTER_EMAIL="test@example.invalid",
            BGIT_HOME=str(self.base / "backups"), GIT_TERMINAL_PROMPT="0",
        )
        self.environment = patch.dict(os.environ, clean_env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.git("init", "-b", "main")
        self.git("config", "core.autocrlf", "false")
        self.write("tracked.txt", "original\n")
        self.git("add", ".")
        self.git("commit", "-m", "initial")
        self.repo = Repository(self.root)
        self.initial = self.repo.initialize()

    def git(self, *args, check=True):
        return subprocess.run(["git", "-C", str(self.root), *args], check=check, capture_output=True).stdout

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, bytes):
            target.write_bytes(value)
        else:
            target.write_text(value, encoding="utf-8", newline="")
        return target

    def protected(self, *args):
        with self.repo.store.lock():
            return self.repo.run(list(args), self.root)
