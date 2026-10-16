import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from bgit.repository import Repository, discover
from bgit.storage import BGitError, atomic_json
from tests.helpers import RepoCase


class RecoveryTests(RepoCase):
    def test_hard_reset_recovers_staged_and_unstaged_versions(self):
        self.write("tracked.txt", "staged\n")
        self.git("add", "tracked.txt")
        self.write("tracked.txt", "unstaged\n")
        self.protected("reset", "--hard")
        self.assertEqual((self.root / "tracked.txt").read_text(), "original\n")
        self.repo.undo()
        self.assertEqual((self.root / "tracked.txt").read_text(), "unstaged\n")
        self.assertEqual(self.git("show", ":tracked.txt"), b"staged\n")

    def test_clean_recovers_untracked_ignored_and_empty_directories(self):
        self.write(".gitignore", "ignored/\n")
        self.write("ignored/secret", "local only")
        self.write("untracked.txt", "new work")
        (self.root / "empty").mkdir()
        self.protected("clean", "-fdx")
        self.assertFalse((self.root / "untracked.txt").exists())
        self.repo.undo()
        self.assertEqual((self.root / "ignored/secret").read_text(), "local only")
        self.assertEqual((self.root / "untracked.txt").read_text(), "new work")
        self.assertTrue((self.root / "empty").is_dir())

    def test_git_restore_discard_is_recoverable(self):
        self.write("tracked.txt", "valuable")
        self.protected("restore", ".")
        self.repo.undo()
        self.assertEqual((self.root / "tracked.txt").read_text(), "valuable")

    def test_deleted_stash_stack_recovers_after_git_gc(self):
        for text in ("first", "second"):
            self.write("tracked.txt", text)
            self.git("stash", "push", "-m", text)
        before = self.git("stash", "list")
        self.protected("stash", "clear")
        self.git("reflog", "expire", "--expire=now", "--all")
        self.git("gc", "--prune=now")
        self.assertEqual(self.git("stash", "list"), b"")
        self.repo.undo()
        self.assertEqual(self.git("stash", "list"), before)
        self.git("stash", "apply", "stash@{1}")
        self.assertEqual((self.root / "tracked.txt").read_text(), "first")

    def test_deleted_branch_restored(self):
        self.git("branch", "important")
        self.protected("branch", "-D", "important")
        self.repo.undo()
        self.assertIn(b"important", self.git("branch", "--list"))

    def test_detached_head_restored(self):
        self.git("checkout", "--detach")
        self.write("tracked.txt", "detached")
        self.git("commit", "-am", "detached")
        head = self.git("rev-parse", "HEAD")
        self.protected("switch", "main")
        self.repo.undo()
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(self.git("branch", "--show-current"), b"")

    def test_rebase_history_can_be_recovered(self):
        self.git("switch", "-c", "feature")
        self.write("feature", "feature")
        self.git("add", ".")
        self.git("commit", "-m", "feature")
        original = self.git("rev-parse", "HEAD")
        self.git("switch", "main")
        self.write("main", "main")
        self.git("add", ".")
        self.git("commit", "-m", "main update")
        self.git("switch", "feature")
        self.assertEqual(self.protected("rebase", "main"), 0)
        self.assertNotEqual(self.git("rev-parse", "HEAD"), original)
        self.repo.undo()
        self.assertEqual(self.git("rev-parse", "HEAD"), original)
        self.assertEqual(self.git("branch", "--show-current").strip(), b"feature")

    def test_conflicted_merge_state_and_index_recover(self):
        self.git("switch", "-c", "other")
        self.write("tracked.txt", "other\n")
        self.git("commit", "-am", "other")
        self.git("switch", "main")
        self.write("tracked.txt", "main\n")
        self.git("commit", "-am", "main")
        self.git("merge", "other", check=False)
        conflict = (self.root / "tracked.txt").read_bytes()
        index = self.git("ls-files", "--unmerged")
        self.assertTrue(index)
        self.protected("merge", "--abort")
        self.repo.undo()
        self.assertEqual((self.root / "tracked.txt").read_bytes(), conflict)
        self.assertEqual(self.git("ls-files", "--unmerged"), index)
        self.assertTrue((self.root / ".git/MERGE_HEAD").exists())

    def test_undo_is_itself_reversible(self):
        self.write("tracked.txt", "before reset")
        self.protected("reset", "--hard")
        self.repo.undo()
        self.repo.undo()
        self.assertEqual((self.root / "tracked.txt").read_text(), "original\n")

    def test_restoration_does_not_delete_future_snapshots(self):
        self.write("tracked.txt", "future")
        future = self.repo.snapshot("future")
        old_paths = {p.name: p.read_bytes() for p in self.repo.store.snapshots.iterdir()}
        self.repo.restore(self.initial["id"])
        for name, data in old_paths.items():
            self.assertEqual((self.repo.store.snapshots / name).read_bytes(), data)
        self.repo.restore(future["id"])
        self.assertEqual((self.root / "tracked.txt").read_text(), "future")

    def test_restore_removes_new_paths_but_checkpoints_them(self):
        self.write("new/file", "keep me")
        checkpoint = self.repo.restore(self.initial["id"])
        self.assertFalse((self.root / "new").exists())
        self.repo.restore(checkpoint["id"])
        self.assertEqual((self.root / "new/file").read_text(), "keep me")

    def test_file_directory_type_changes(self):
        self.write("shape", "file")
        before = self.repo.snapshot("file")
        (self.root / "shape").unlink()
        self.write("shape/child", "directory")
        self.repo.restore(before["id"])
        self.assertEqual((self.root / "shape").read_text(), "file")

    def test_binary_and_unusual_names(self):
        name = "space and unicode-雪.bin" if os.name == "nt" else "space and\nnewline-雪.bin"
        data = bytes(range(256))
        self.write(name, data)
        saved = self.repo.snapshot("binary")
        (self.root / name).unlink()
        self.repo.restore(saved["id"])
        self.assertEqual((self.root / name).read_bytes(), data)

    @unittest.skipIf(os.name == "nt", "Windows reparse points are explicitly unsupported")
    def test_symlinks_are_not_followed(self):
        outside = self.base / "outside"
        outside.write_text("outside")
        (self.root / "link").symlink_to(outside)
        snapshot = self.repo.snapshot("link")
        self.assertEqual(snapshot["entries"]["link"]["type"], "symlink")
        (self.root / "link").unlink()
        self.write("link", "regular now")
        self.repo.restore(snapshot["id"])
        self.assertTrue((self.root / "link").is_symlink())
        self.assertEqual(outside.read_text(), "outside")

    @unittest.skipIf(os.name == "nt", "POSIX executable permissions")
    def test_executable_mode(self):
        path = self.write("script", "#!/bin/sh\n")
        path.chmod(0o755)
        snapshot = self.repo.snapshot("executable")
        path.chmod(0o644)
        self.repo.restore(snapshot["id"])
        self.assertEqual(path.stat().st_mode & 0o777, 0o755)

    @unittest.skipIf(os.name == "nt", "POSIX directory permissions")
    def test_readonly_directory_can_be_restored_and_undone(self):
        self.write("readonly/file", "saved")
        directory = self.root / "readonly"
        directory.chmod(0o555)
        saved = self.repo.snapshot("read only")
        self.repo.restore(self.initial["id"])
        self.repo.restore(saved["id"])
        self.assertEqual((directory / "file").read_text(), "saved")
        self.assertEqual(directory.stat().st_mode & 0o777, 0o555)
        directory.chmod(0o755)

    def test_clock_rollback_does_not_reorder_history(self):
        with patch("bgit.repository.time.time_ns", return_value=1):
            snapshot = self.repo.snapshot("clock moved backward")
        self.assertGreater(snapshot["id"], self.initial["id"])
        self.assertEqual(self.repo.timeline()[-1]["id"], snapshot["id"])

    def test_export_full_repository(self):
        destination = self.base / "recovered"
        self.repo.recover(self.initial["id"], destination)
        self.assertEqual((destination / "tracked.txt").read_text(), "original\n")
        self.assertTrue((destination / ".git/HEAD").is_file())

    def test_export_single_file_does_not_change_live_repository(self):
        self.write("tracked.txt", "current")
        destination = self.base / "recovered"
        self.repo.recover(self.initial["id"], destination, "tracked.txt")
        self.assertEqual((destination / "tracked.txt").read_text(), "original\n")
        self.assertEqual((self.root / "tracked.txt").read_text(), "current")
        self.assertFalse((destination / ".git").exists())

    def test_export_nested_directory(self):
        self.write("src/nested/file", "nested")
        snapshot = self.repo.snapshot("nested")
        destination = self.base / "recovered"
        self.repo.recover(snapshot["id"], destination, "src/nested")
        self.assertEqual((destination / "src/nested/file").read_text(), "nested")

    def test_existing_export_directory_rejected(self):
        with self.assertRaises(BGitError):
            self.repo.recover(self.initial["id"], self.base)

    def test_export_inside_repository_rejected(self):
        with self.assertRaises(BGitError):
            self.repo.recover(self.initial["id"], self.root / "recovered")

    def test_export_git_metadata_selection_rejected(self):
        with self.assertRaises(BGitError):
            self.repo.recover(self.initial["id"], self.base / "recovered", ".git/config")

    def test_corrupted_backup_never_changes_current_workspace(self):
        digest = self.initial["entries"]["tracked.txt"]["object"]
        self.repo.store.object_path(digest).write_bytes(b"corrupt")
        self.write("tracked.txt", "current")
        with self.assertRaises(BGitError):
            self.repo.restore(self.initial["id"])
        self.assertEqual((self.root / "tracked.txt").read_text(), "current")
        self.assertFalse(self.repo.pending.exists())

    def test_failed_checkpoint_prevents_git_execution(self):
        self.write("tracked.txt", "current")
        with patch.object(self.repo.store, "put", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.protected("reset", "--hard")
        self.assertEqual((self.root / "tracked.txt").read_text(), "current")

    def test_failed_command_retains_checkpoint_and_exit_code(self):
        count = len(self.repo.timeline())
        self.assertNotEqual(self.protected("reset", "missing-ref"), 0)
        self.assertEqual(len(self.repo.timeline()), count + 1)

    def test_interrupted_restore_can_resume_without_git_metadata(self):
        self.write("tracked.txt", "current")
        def interrupt(staged):
            shutil.rmtree(self.root / ".git")
            raise OSError("simulated interruption")
        with patch.object(self.repo, "_replace_tree", side_effect=interrupt):
            with self.assertRaises(OSError):
                self.repo.restore(self.initial["id"])
        self.assertTrue(self.repo.pending.exists())
        self.repo.resume()
        self.assertFalse(self.repo.pending.exists())
        self.assertEqual((self.root / "tracked.txt").read_text(), "original\n")
        self.assertTrue(self.git("rev-parse", "HEAD"))

    def test_interrupted_restore_can_rollback(self):
        self.write("tracked.txt", "current")
        with patch.object(self.repo, "_replace_tree", side_effect=OSError("interruption")):
            with self.assertRaises(OSError):
                self.repo.restore(self.initial["id"])
        self.repo.resume(rollback=True)
        self.assertEqual((self.root / "tracked.txt").read_text(), "current")

    def test_pending_restore_blocks_new_destructive_operation(self):
        atomic_json(self.repo.pending, {"target": self.initial["id"], "rollback": self.initial["id"]})
        with self.assertRaisesRegex(BGitError, "interrupted"):
            self.protected("reset", "--hard")

    def test_changed_file_during_snapshot_is_rejected(self):
        original_put = self.repo.store.put
        # Use a controlled mutation after the first object is persisted.
        changed = False
        def mutate_once(stream):
            nonlocal changed
            digest = original_put(stream)
            if not changed:
                changed = True
                self.write("new-during-snapshot", "racing writer")
            return digest
        count = len(self.repo.timeline())
        with patch.object(self.repo.store, "put", side_effect=mutate_once):
            with self.assertRaisesRegex(BGitError, "changed"):
                self.repo.snapshot("race")
        self.assertEqual(len(self.repo.timeline()), count)

    def test_git_lock_blocks_snapshot(self):
        self.write(".git/index.lock", "")
        with self.assertRaisesRegex(BGitError, "lock"):
            self.repo.snapshot("locked")

    def test_nested_repository_rejected(self):
        (self.root / "nested/.git").mkdir(parents=True)
        with self.assertRaisesRegex(BGitError, "Nested"):
            self.repo.snapshot("nested")

    def test_linked_worktree_rejected(self):
        self.git("worktree", "add", "-b", "linked", str(self.base / "linked"))
        with self.assertRaisesRegex(BGitError, "worktrees"):
            self.repo.snapshot("worktree")

    def test_alternate_object_store_rejected(self):
        self.write(".git/objects/info/alternates", "/some/other/objects")
        with self.assertRaisesRegex(BGitError, "Shared"):
            self.repo.snapshot("shared")

    @unittest.skipIf(os.name == "nt", "POSIX FIFO")
    def test_special_file_rejected(self):
        os.mkfifo(self.root / "pipe")
        with self.assertRaisesRegex(BGitError, "Special"):
            self.repo.snapshot("fifo")

    def test_store_inside_repository_rejected(self):
        with self.assertRaises(BGitError):
            Repository(self.root, self.root / ".bgit")

    def test_store_containing_repository_rejected(self):
        with self.assertRaises(BGitError):
            Repository(self.root, self.base)

    def test_git_environment_override_rejected(self):
        with patch.dict(os.environ, {"GIT_INDEX_FILE": str(self.base / "index")}):
            with self.assertRaises(BGitError):
                self.repo.snapshot("override")

    def test_discovery_from_subdirectory(self):
        (self.root / "src").mkdir()
        self.assertEqual(discover(self.root / "src"), self.root)

    def test_double_initialization_rejected(self):
        with self.assertRaises(BGitError):
            self.repo.initialize()

    def test_empty_repository_supported(self):
        empty = self.base / "empty-repo"
        empty.mkdir()
        import subprocess
        subprocess.run(["git", "init", str(empty)], check=True, capture_output=True)
        repo = Repository(empty)
        snapshot = repo.initialize()
        repo.restore(snapshot["id"])
        self.assertTrue((empty / ".git/HEAD").exists())

    def test_unsupported_command_and_alias_rejected(self):
        for command in ("push", "config", "my-alias", "-C"):
            with self.subTest(command=command), self.assertRaises(BGitError):
                self.protected(command)

    def test_undo_without_command_rejected(self):
        with self.assertRaisesRegex(BGitError, "Nothing"):
            self.repo.undo()

    def test_snapshot_selector_rejects_path_traversal(self):
        for selector in ("../", "", "*", "missing"):
            with self.subTest(selector=selector), self.assertRaises(BGitError):
                self.repo.load(selector)

    def test_manifest_path_traversal_rejected(self):
        snapshot = self.repo.load(self.initial["id"])
        snapshot["entries"]["../outside"] = {"type": "directory", "mode": 0o755}
        atomic_json(self.repo.store.snapshots / (snapshot["id"] + ".json"), snapshot)
        with self.assertRaisesRegex(BGitError, "Unsafe"):
            self.repo.load(snapshot["id"])

    def test_manifest_symlink_parent_rejected(self):
        snapshot = self.repo.load(self.initial["id"])
        snapshot["entries"]["escape"] = {"type": "symlink", "mode": 0o777, "target": "/tmp"}
        snapshot["entries"]["escape/child"] = {"type": "directory", "mode": 0o755}
        atomic_json(self.repo.store.snapshots / (snapshot["id"] + ".json"), snapshot)
        with self.assertRaises(BGitError):
            self.repo.load(snapshot["id"])
