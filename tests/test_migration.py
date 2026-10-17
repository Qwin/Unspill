"""The rename must never hide, fork, or rewrite a user's existing history."""

import os
from pathlib import Path
from unittest.mock import patch

from unspill.repository import Repository
from unspill.storage import UnspillError
from tests.helpers import RepoCase


class MigrationTests(RepoCase):
    def homes(self, legacy=False):
        return self.base / ('backups' if legacy else 'new-backups')

    def test_legacy_default_history_is_reused_and_restores(self):
        before = {p.name: p.read_bytes() for p in self.repo.store.snapshots.glob('*.json')}
        with patch.dict(os.environ, {}, clear=True), patch('unspill.repository.default_home', side_effect=self.homes):
            migrated = Repository(self.root)
            migrated.require_initialized()
            self.assertEqual(migrated.store.path, self.repo.store.path)
            self.write('tracked.txt', 'accidental change')
            migrated.restore(self.initial['id'])
        self.assertEqual((self.root / 'tracked.txt').read_text(), 'original\n')
        for name, data in before.items():
            self.assertEqual((self.repo.store.snapshots / name).read_bytes(), data)
        self.assertFalse((self.base / 'new-backups').exists())

    def test_legacy_environment_variable_still_works(self):
        with patch.dict(os.environ, {'BGIT_HOME': str(self.base / 'backups')}, clear=True):
            migrated = Repository(self.root)
            migrated.require_initialized()
            self.assertEqual(migrated.store.path, self.repo.store.path)

    def test_new_variable_takes_precedence(self):
        with patch.dict(os.environ, {'UNSPILL_HOME': str(self.base / 'backups'), 'BGIT_HOME': str(self.base / 'other')}, clear=True):
            Repository(self.root).require_initialized()

    def test_explicit_home_takes_precedence(self):
        with patch.dict(os.environ, {'UNSPILL_HOME': str(self.base / 'other')}, clear=True):
            Repository(self.root, self.base / 'backups').require_initialized()

    def test_two_default_histories_require_explicit_selection(self):
        new_store = self.base / 'new-backups/repositories' / self.repo.store.path.name
        new_store.mkdir(parents=True)
        with patch.dict(os.environ, {}, clear=True), patch('unspill.repository.default_home', side_effect=self.homes):
            with self.assertRaisesRegex(UnspillError, 'Two backup histories'):
                Repository(self.root)
        self.repo.require_initialized()

    def test_fresh_repository_uses_new_default(self):
        fresh = self.base / 'fresh'
        with patch.dict(os.environ, {}, clear=True), patch('unspill.repository.default_home', side_effect=self.homes):
            selected = Repository(fresh)
        self.assertTrue(selected.store.path.is_relative_to(self.base / 'new-backups'))

    def test_unrelated_legacy_store_is_not_accepted(self):
        marker = self.repo.store.path / 'repository.json'
        marker.write_text('{"version":1,"root":"/another/project"}')
        with patch.dict(os.environ, {}, clear=True), patch('unspill.repository.default_home', side_effect=self.homes):
            with self.assertRaisesRegex(UnspillError, 'does not match'):
                Repository(self.root).require_initialized()
