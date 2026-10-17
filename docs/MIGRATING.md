# Upgrading from BGit to Unspill

The project and command are now **Unspill** (`unspill`). This project is independent
of other software named bgit. Its owner remains Robert Al-Malak / Qwin and its
license remains Apache-2.0. The rename does not change the v1 backup format.

## Install the new command

```sh
pipx install "git+https://github.com/Qwin/Unspill.git@v0.4.0-alpha.1"
unspill --version
cd your-existing-project
unspill timeline
unspill verify
```

For standalone installations, use the new `unspill` executable from the
[release downloads](https://github.com/Qwin/Unspill/releases). Git is still needed.
There is no `bgit` executable alias in the new package, to avoid a command collision.
After verifying access to your history, you can uninstall your old pipx `bgit`
installation. Do not delete your backup directories. Update scripts to use
`unspill` or `python -m unspill`; the import package has changed too.

## Your existing backups

No snapshots are moved, rewritten, merged, or deleted by this upgrade.

- `UNSPILL_HOME` selects a custom store; use the same directory as before.
- An existing `BGIT_HOME` setting is accepted when `UNSPILL_HOME` is not set.
- With neither variable set, Unspill discovers an existing store for this exact
  repository in the former default location (`~/.local/share/bgit` on POSIX or
  `%LOCALAPPDATA%\BGit` on Windows) and continues using it in place.
- Fresh repositories use `~/.local/share/unspill` or `%LOCALAPPDATA%\Unspill`.
- If both defaults contain a history for the same repository, Unspill stops and
  asks you to select one explicitly with `UNSPILL_HOME`.

Keep your protected repository at the same absolute path; the rename does not add
repository-relocation support. Do not run `init` again to upgrade an initialized
repository. Use `timeline` and `verify` first. Old snapshot labels may still contain
the old product name because captured records are immutable.

If you configured a custom store, for example:

```sh
export UNSPILL_HOME=/the/same/external/backup-directory
unspill timeline
```

In PowerShell:

```powershell
$env:UNSPILL_HOME = 'C:\your-existing-backup-directory'
unspill timeline
unspill restore '@18' --dry-run
```

Quote numbered selectors in PowerShell. Existing historical Git tags are retained
for reproducibility; their source and executables still use their original name.
Use the Unspill release for new installations.

[README](../README.md) · [Installation](INSTALL.md)
