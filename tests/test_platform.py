import os
from pathlib import Path
import subprocess
import sys
import unittest

from bgit.platform import windows_path_is_safe
from bgit.repository import descriptor_matches, fingerprint
from bgit.storage import BGitError
from tests.helpers import RepoCase


class WindowsPathTests(unittest.TestCase):
    def test_regular_paths(self):
        for path in ("src/main.py", ".git/HEAD", "space and unicode-雪.bin", "com10.txt"):
            with self.subTest(path=path):
                self.assertTrue(windows_path_is_safe(path))

    def test_windows_special_paths(self):
        for path in ("C:/escape", "C:escape", "file:stream", "dir\\escape", "CON", "nul.txt",
                     "src/LPT1.log", "COM¹", "trailing.", "trailing ", "a?b", "a\nb"):
            with self.subTest(path=path):
                self.assertFalse(windows_path_is_safe(path))


class PlatformRecoveryTests(RepoCase):
    def test_descriptor_and_path_comparison_for_modified_file(self):
        path = self.write("metadata.txt", "initial")
        path.write_text("modified content")
        with path.open("rb") as stream:
            self.assertTrue(descriptor_matches(fingerprint(os.fstat(stream.fileno())), fingerprint(path.lstat())))

    def test_readonly_file_restore(self):
        path = self.write("readonly.txt", "before")
        path.chmod(0o444)
        snapshot = self.repo.snapshot("read only file")
        self.repo.restore(self.initial["id"])
        self.repo.restore(snapshot["id"])
        self.assertEqual(path.read_text(), "before")
        path.chmod(0o644)

    def test_lock_is_exclusive_across_processes(self):
        code = "from pathlib import Path; from bgit.storage import Store; import sys; s=Store(Path(sys.argv[1]));\nwith s.lock(): pass"
        with self.repo.store.lock():
            result = subprocess.run([sys.executable, "-c", code, str(self.repo.store.path)],
                                    capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Another BGit operation", result.stderr)

    def test_permission_failure_inside_lock_is_not_reported_as_contention(self):
        with self.assertRaisesRegex(PermissionError, "actual file failure"):
            with self.repo.store.lock():
                raise PermissionError("actual file failure")

    @unittest.skipUnless(os.name == "nt", "Windows junction handling")
    def test_junction_rejected_without_traversing_target(self):
        target = self.base / "outside"
        target.mkdir()
        (target / "valuable.txt").write_text("outside")
        junction = self.root / "junction"
        subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(target)],
                       check=True, capture_output=True)
        try:
            with self.assertRaisesRegex(BGitError, "reparse"):
                self.repo.snapshot("junction")
        finally:
            junction.rmdir()
        self.assertEqual((target / "valuable.txt").read_text(), "outside")
