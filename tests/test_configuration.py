"""Store selection belongs to Unspill only."""

import os
from unittest.mock import patch

from unspill.repository import Repository
from tests.helpers import RepoCase


class ConfigurationTests(RepoCase):
    def test_default_ignores_former_setting(self):
        default = self.base / 'unspill-default'
        with patch.dict(os.environ, {'BGIT_HOME': str(self.base / 'backups')}, clear=True), patch('unspill.repository.default_home', return_value=default):
            selected = Repository(self.root)
        self.assertTrue(selected.store.path.is_relative_to(default))
        self.assertNotEqual(selected.store.path, self.repo.store.path)

    def test_unspill_setting_selects_store(self):
        with patch.dict(os.environ, {'UNSPILL_HOME': str(self.base / 'backups')}, clear=True):
            Repository(self.root).require_initialized()

    def test_explicit_home_overrides_environment(self):
        with patch.dict(os.environ, {'UNSPILL_HOME': str(self.base / 'other')}, clear=True):
            Repository(self.root, self.base / 'backups').require_initialized()
