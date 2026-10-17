# Unspill — get your work back

Keep your uncommitted work, staging, branches, and stashes recoverable before risky
Git operations. Find a checkpoint by its action, branch, commit message, or file
history, then preview and recover it.

**Public alpha for Windows, macOS, and Linux.** Created by Robert Al-Malak
([Qwin](https://github.com/Qwin)). [Apache-2.0](LICENSE).

An independent recovery tool for Git® workspaces.

## Install

With Git, Python 3.11+, and pipx installed:

```sh
pipx install "git+https://github.com/Qwin/Unspill.git@v0.4.0-alpha.1"
```

Prefer a standalone executable? [Download a release](https://github.com/Qwin/Unspill/releases)
for Windows x64, macOS Intel/Apple Silicon, or Linux x64. Git is still required.
See the [installation guide](docs/INSTALL.md) for setup, checksums, and updating.

## Already have a Git repository?

Yes—start inside your existing checkout. No migration or new remote is needed.
Your normal Git tools still work.

```sh
cd your-existing-project
unspill init
unspill snapshot -m "Login changes before the cleanup"
unspill git reset --hard HEAD
unspill recover
```

`unspill init` captures the current repository. Use `unspill git` for automatic
checkpoints before supported operations. Ordinary `git` commands and edits are
not automatically captured; take a manual snapshot whenever you need one.

## Find the right moment

```sh
unspill timeline
unspill timeline --search "login"
```

Illustrative timeline entry:

```text
#18  2026-10-16 10:42:00 MST  feature/login
  Before git reset --hard HEAD
  Commit: Add password validation [a12bc345]
  Saved: 1 staged, 2 unstaged, 1 untracked; 0 stashes
    MM src/login.py
     M src/errors.py
    ?? notes.txt
  Operation outcome: completed
  Select: @18  |  ID: <full-snapshot-id>
```

The checkpoint is the state **before** the named action. `@18` is a stable local
choice so you do not need to copy a long ID. Use the full snapshot ID when you need a permanent reference in a script.

## Recover your work

```sh
unspill recover                         # Guided picker, preview, restore or export
unspill undo                            # Restore the latest pre-operation state
unspill restore @18 --dry-run            # Preview a particular checkpoint
unspill recover @18 --path src/login.py --to ../rescued-file
```

The last command exports `src/login.py` into a new folder. Full restoration saves
your current state first and keeps every later checkpoint: you can go forward
again. Preview before restoring to see files and Git state that would change.

## Learn more

- [All commands and recovery examples](docs/COMMANDS.md): file history, text diffs,
  search, full restore, exports, verification, and interrupted recovery.
- [Installation and downloads](docs/INSTALL.md)
- [Storage, supported repositories, and limitations](docs/STORAGE.md)
- [Testing and runnable recovery demos](docs/TESTING.md)
- [Architecture](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md),
  [contributing](CONTRIBUTING.md), [naming research](docs/NAMING.md), and [changelog](CHANGELOG.md)

## Know what is protected

Unspill captures **ignored files too**, so backups may contain credentials and secrets.
Backups live outside the repository, are not encrypted, and have no automatic
expiry. Pause other tools that write to the repository during capture or recovery.
Only captured work can be recovered; local history cannot undo remote pushes or
survive loss of the backup disk. Linked worktrees, submodules, sparse/partial
clones, and Windows symlinks/junctions are currently unsupported.

This is an early recovery tool: keep independent backups of valuable work.
See [security and data handling](SECURITY.md) for details.
