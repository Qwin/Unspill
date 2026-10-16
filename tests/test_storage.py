import io
import os
from pathlib import Path
import tempfile
import unittest
import zlib

from bgit.storage import BGitError, Store, atomic_json, read_json


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "store")
        self.store.create()

    def test_roundtrip_binary(self):
        data = bytes(range(256)) * 10000
        digest = self.store.put(io.BytesIO(data))
        output = io.BytesIO()
        self.store.extract(digest, output)
        self.assertEqual(data, output.getvalue())

    def test_empty_object(self):
        digest = self.store.put(io.BytesIO(b""))
        self.store.extract(digest, io.BytesIO())

    def test_deduplication(self):
        one = self.store.put(io.BytesIO(b"same"))
        two = self.store.put(io.BytesIO(b"same"))
        self.assertEqual(one, two)
        self.assertEqual(len(list(self.store.objects.iterdir())), 1)

    def test_compression(self):
        digest = self.store.put(io.BytesIO(b"a" * 100000))
        self.assertLess(self.store.object_path(digest).stat().st_size, 1000)

    def test_corruption_detected(self):
        digest = self.store.put(io.BytesIO(b"original"))
        self.store.object_path(digest).write_bytes(zlib.compress(b"modified"))
        with self.assertRaisesRegex(BGitError, "checksum"):
            self.store.extract(digest, None)

    def test_corrupt_existing_object_not_reused(self):
        digest = self.store.put(io.BytesIO(b"original"))
        self.store.object_path(digest).write_bytes(b"broken")
        with self.assertRaises(BGitError):
            self.store.put(io.BytesIO(b"original"))

    def test_truncated_object(self):
        digest = self.store.put(io.BytesIO(b"original"))
        path = self.store.object_path(digest)
        path.write_bytes(path.read_bytes()[:-2])
        with self.assertRaises(BGitError):
            self.store.extract(digest, None)

    def test_trailing_data_rejected(self):
        digest = self.store.put(io.BytesIO(b"original"))
        path = self.store.object_path(digest)
        path.write_bytes(path.read_bytes() + b"junk")
        with self.assertRaises(BGitError):
            self.store.extract(digest, None)

    def test_missing_object(self):
        with self.assertRaises(BGitError):
            self.store.extract("0" * 64, None)

    def test_object_path_traversal(self):
        for digest in ("../outside", "", None, "A" * 64):
            with self.subTest(digest=digest), self.assertRaises(BGitError):
                self.store.object_path(digest)

    def test_immutable_record_cannot_be_replaced(self):
        path = self.store.path / "record.json"
        atomic_json(path, {"a": 1}, immutable=True)
        with self.assertRaises(FileExistsError):
            atomic_json(path, {"a": 2}, immutable=True)
        self.assertEqual(read_json(path), {"a": 1})

    def test_mutable_record_atomic_update(self):
        path = self.store.path / "record.json"
        atomic_json(path, {"a": 1})
        atomic_json(path, {"a": 2})
        self.assertEqual(read_json(path), {"a": 2})

    def test_invalid_json(self):
        path = self.store.path / "record.json"
        for content in ("[1]", "broken"):
            path.write_text(content)
            with self.assertRaises(BGitError):
                read_json(path)

    def test_exclusive_lock(self):
        with self.store.lock():
            with self.assertRaisesRegex(BGitError, "Another"):
                with self.store.lock():
                    self.fail("Lock unexpectedly acquired")

    def test_lock_released_on_exception(self):
        with self.assertRaises(ValueError):
            with self.store.lock():
                raise ValueError("failure")
        with self.store.lock():
            pass

    def test_failed_write_removes_temporary_object(self):
        class BrokenStream:
            def read(self, size):
                raise OSError("disk error")
        with self.assertRaises(OSError):
            self.store.put(BrokenStream())
        self.assertEqual(list(self.store.objects.iterdir()), [])

    @unittest.skipIf(os.name == "nt", "Windows uses inherited ACLs instead of POSIX modes")
    def test_private_store_permissions(self):
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o700)
