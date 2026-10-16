import json
import os
from pathlib import Path
import subprocess
import sys

from tests.helpers import RepoCase


class CliTests(RepoCase):
    def cli(self, *args, cwd=None):
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
        return subprocess.run([sys.executable, "-m", "bgit", *args],
                              cwd=cwd or self.root, env=env, capture_output=True, text=True)

    def test_help(self):
        result = self.cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("recover", result.stdout)

    def test_version(self):
        self.assertIn("0.2.0", self.cli("--version").stdout)

    def test_no_command_shows_help(self):
        self.assertIn("usage:", self.cli().stdout)

    def test_timeline_json(self):
        result = self.cli("timeline", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["id"], self.initial["id"])

    def test_inspect(self):
        result = self.cli("inspect", self.initial["id"])
        self.assertIn("tracked.txt", json.loads(result.stdout)["paths"])

    def test_named_snapshot(self):
        result = self.cli("snapshot", "-m", "before experiment")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.repo.load(result.stdout.strip())["label"], "before experiment")

    def test_restore_dry_run_changes_nothing(self):
        self.write("tracked.txt", "current")
        count = len(self.repo.timeline())
        result = self.cli("restore", self.initial["id"], "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "tracked.txt").read_text(), "current")
        self.assertEqual(len(self.repo.timeline()), count)

    def test_protected_reset_and_undo(self):
        self.write("tracked.txt", "valuable")
        result = self.cli("git", "reset", "--hard")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli("undo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "tracked.txt").read_text(), "valuable")

    def test_direct_reset_shorthand(self):
        self.assertEqual(self.cli("reset", "--hard").returncode, 0)

    def test_git_restore_not_confused_with_bgit_restore(self):
        self.write("tracked.txt", "valuable")
        self.assertEqual(self.cli("git", "restore", ".").returncode, 0)
        self.assertEqual((self.root / "tracked.txt").read_text(), "original\n")

    def test_invalid_snapshot_is_friendly_error(self):
        result = self.cli("restore", "000000")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Snapshot ID", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_git_failure_exit_code(self):
        result = self.cli("git", "reset", "missing-ref")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.repo.timeline()[-1]["kind"], "before-command")

    def test_verify(self):
        result = self.cli("verify")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Verified 1 snapshots", result.stdout)

    def test_recover_file(self):
        output = self.base / "export"
        result = self.cli("recover", self.initial["id"], "--path", "tracked.txt", "--to", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / "tracked.txt").exists())

    def test_repo_option_from_outside_repository(self):
        result = self.cli("--repo", str(self.root), "timeline", "--json", cwd=self.base)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_subdirectory_git_arguments_keep_relative_meaning(self):
        self.write("src/file", "original")
        self.git("add", ".")
        self.git("commit", "-m", "nested")
        self.write("src/file", "modified")
        result = self.cli("git", "restore", "file", cwd=self.root / "src")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "src/file").read_text(), "original")

    def test_status_does_not_add_snapshot(self):
        count = len(self.repo.timeline())
        self.assertEqual(self.cli("git", "status", "--short").returncode, 0)
        self.assertEqual(len(self.repo.timeline()), count)
