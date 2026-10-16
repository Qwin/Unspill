import contextlib
import io
import json
from unittest.mock import patch

from bgit.navigation import entry_text, file_diff, file_history, find_records, numbered, preview, safe
from bgit.storage import BGitError, atomic_json
from bgit.wizard import recover_interactively
from tests.helpers import RepoCase


class NavigationTests(RepoCase):
    def test_context_captures_branch_commit_and_staging(self):
        self.write("tracked.txt", "staged")
        self.git("add", "tracked.txt")
        self.write("tracked.txt", "unstaged")
        self.write("new.txt", "untracked")
        snapshot = self.repo.snapshot("meaningful checkpoint")
        context = snapshot["context"]
        self.assertEqual(context["branch"], "main")
        self.assertEqual(context["subject"], "initial")
        self.assertEqual(context["commit"], self.git("rev-parse", "HEAD").decode().strip())
        self.assertIn({"status": "MM", "path": "tracked.txt"}, context["changes"])
        self.assertIn({"status": "??", "path": "new.txt"}, context["changes"])

    def test_action_description_has_reset_mode_and_ref(self):
        self.assertEqual(self.repo.action_description(["reset", "--hard", "HEAD"]), "git reset --hard HEAD")

    def test_action_description_omits_arbitrary_arguments(self):
        self.assertEqual(self.repo.action_description(["fetch", "https://user:secret@example.invalid/repo"]), "git fetch")
        self.assertEqual(self.repo.action_description(["commit", "-m", "secret message"]), "git commit")

    def test_outcome_recorded_without_mutating_snapshot(self):
        self.protected("reset", "--hard")
        checkpoint = self.repo.timeline()[-1]
        path = self.repo.store.snapshots / (checkpoint["id"] + ".json")
        before = path.read_bytes()
        self.assertEqual(numbered(self.repo)[-1]["outcome"], "completed")
        self.assertEqual(path.read_bytes(), before)

    def test_failed_operation_is_described(self):
        self.protected("reset", "missing-ref")
        self.assertEqual(numbered(self.repo)[-1]["outcome"], "failed")

    def test_numbers_stay_stable_after_more_snapshots(self):
        self.repo.snapshot("second")
        self.assertEqual(self.repo.load("@1")["id"], self.initial["id"])
        self.repo.snapshot("third")
        self.assertEqual(self.repo.load("@1")["id"], self.initial["id"])
        with self.assertRaises(BGitError):
            self.repo.load("@999")

    def test_search_label_branch_and_filename(self):
        self.write("login.py", "work")
        self.repo.snapshot("before login experiment")
        self.assertEqual(len(find_records(self.repo, "login.py")), 1)
        self.assertEqual(len(find_records(self.repo, "experiment", "main")), 1)
        self.assertEqual(find_records(self.repo, branch="other"), [])

    def test_preview_identifies_overwrites_removals_and_recovered_files(self):
        self.write("recover-me", "saved")
        target = self.repo.snapshot("saved")
        (self.root / "recover-me").unlink()
        self.write("tracked.txt", "new")
        self.write("remove-me", "later")
        result = preview(self.repo, target)
        actions = {c["path"]: c["action"] for c in result["changes"]}
        self.assertEqual(actions, {"recover-me": "recover", "remove-me": "remove", "tracked.txt": "replace"})
        self.assertEqual((self.root / "tracked.txt").read_text(), "new")

    def test_preview_distinguishes_index_changes(self):
        self.write("tracked.txt", "staged")
        self.git("add", "tracked.txt")
        result = preview(self.repo, self.initial)
        self.assertTrue(result["index_changed"])

    def test_text_diff_is_current_to_checkpoint(self):
        self.write("tracked.txt", "later\n")
        result = file_diff(self.repo, self.initial, "tracked.txt")
        self.assertIn("-later", result)
        self.assertIn("+original", result)

    def test_binary_diff_is_not_printed_as_text(self):
        self.write("tracked.txt", b"\0binary")
        self.assertIn("Binary", file_diff(self.repo, self.initial, "tracked.txt"))

    def test_diff_limit(self):
        self.write("tracked.txt", b"x" * (1024 * 1024 + 1))
        self.assertIn("limit", file_diff(self.repo, self.initial, "tracked.txt"))

    def test_history_collapses_identical_captured_versions_and_shows_deletion(self):
        self.repo.snapshot("same")
        self.write("tracked.txt", "changed")
        self.repo.snapshot("changed")
        (self.root / "tracked.txt").unlink()
        self.repo.snapshot("deleted")
        history = file_history(self.repo, "tracked.txt")
        self.assertEqual([s["number"] for s in history], [1, 3, 4])
        self.assertEqual(history[-1]["file_state"], "absent")

    def test_legacy_snapshot_still_loads_and_is_labelled(self):
        snapshot = dict(self.initial)
        snapshot.pop("context")
        atomic_json(self.repo.store.snapshots / (snapshot["id"] + ".json"), snapshot)
        self.assertIn("Legacy snapshot", entry_text(numbered(self.repo)[0]))
        self.repo.restore("@1")

    def test_control_characters_are_escaped(self):
        self.assertNotIn("\x1b", safe("danger\x1b[2J"))

    def test_rename_metadata_does_not_treat_old_path_as_another_file(self):
        self.git("mv", "tracked.txt", "renamed.txt")
        changes = self.repo.snapshot("renamed")["context"]["changes"]
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["path"], "renamed.txt")

    def test_detached_head_has_explicit_label(self):
        self.git("checkout", "--detach")
        self.assertEqual(self.repo.snapshot("detached")["context"]["branch"], "(detached HEAD)")

    def test_stash_names_are_captured(self):
        self.write("tracked.txt", "stash work")
        self.git("stash", "push", "-m", "login experiment")
        self.assertIn("login experiment", self.repo.snapshot("stashes")["context"]["stashes"][0])

    def test_picker_cancellation_is_read_only(self):
        before = len(self.repo.timeline())
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["4", "@1", "q"]), contextlib.redirect_stdout(io.StringIO()):
            recover_interactively(self.repo)
        self.assertEqual(len(self.repo.timeline()), before)

    def test_picker_eof_cancels(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=EOFError), contextlib.redirect_stdout(io.StringIO()) as output:
            recover_interactively(self.repo)
        self.assertIn("Cancelled", output.getvalue())

    def test_picker_full_restore_and_checkpoint(self):
        self.write("tracked.txt", "current")
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["4", "@1", "r"]), contextlib.redirect_stdout(io.StringIO()):
            recover_interactively(self.repo)
        self.assertEqual((self.root / "tracked.txt").read_text(), "original\n")
        self.assertEqual(self.repo.timeline()[-1]["kind"], "before-restore")

    def test_picker_single_file_export_preserves_current_work(self):
        self.write("tracked.txt", "current")
        destination = self.base / "rescued"
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["2", "tracked.txt", "@1", "e", str(destination)]), contextlib.redirect_stdout(io.StringIO()):
            recover_interactively(self.repo)
        self.assertEqual((self.root / "tracked.txt").read_text(), "current")
        self.assertEqual((destination / "tracked.txt").read_text(), "original\n")

    def test_noninteractive_picker_requires_explicit_export(self):
        with patch("sys.stdin.isatty", return_value=False), self.assertRaisesRegex(BGitError, "terminal"):
            recover_interactively(self.repo)
