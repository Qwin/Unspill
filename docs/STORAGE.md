# Storage and protection boundaries

For legacy histories and `BGIT_HOME` compatibility, see [migration](MIGRATING.md).

Default location for new repositories:

```text
~/.local/share/unspill/repositories/<hash-of-absolute-repository-path>/
  repository.json
  snapshots/       # Append-only snapshot manifests
  objects/         # Compressed, SHA-256-addressed file contents
  events/          # Command outcomes and restore completion records
  pending.json     # Present only during an unfinished restore
  lock
```

Set `UNSPILL_HOME` to select a different external location **before initialization**,
and use the same setting for later commands:

```sh
export UNSPILL_HOME=/path/outside/your/projects/unspill-data
unspill init
```

An in-project `.unspill` folder could be removed by `git clean -fdx`. Unspill therefore
refuses stores inside the repository or stores containing the repository.
Unchanged contents share one object; snapshots do not duplicate every file's bytes.
Each snapshot still scans all files. Large repositories and changing Git packfiles
can be expensive. Keep sufficient disk space for backups **and restore staging**.

Repositories are identified by canonical absolute path in this alpha. Moving one does
not automatically reconnect its history. Keep the original store and use the old
root path to recover/export; relocation support is planned.

## Protection boundaries

- Only captured states are recoverable. Ordinary `git` commands, IDE actions, and
  edits do not create checkpoints automatically. There is no background watcher.
- **All files are included, even ignored files**, to recover from `clean -fdx`.
  This includes `.env`, credentials, generated output, and dependency directories.
  Backups are local and **not encrypted**. POSIX stores use mode 0700; Windows stores inherit the containing user directory’s ACLs.
  There are no exclusion rules in this alpha; do not use it where permanent capture of
  these files is unacceptable. Removing a secret from Git does not remove it here.
- Stop concurrent Git processes, builds, editors that save, and other writers
  during operations. Unspill locks other Unspill processes, rejects existing Git locks,
  and detects common capture races. It cannot freeze arbitrary processes or
  guarantee a consistent capture while external writers are active.
- If checkpoint creation fails, the protected command does not run. Restore
  verifies and stages target contents before changing the live repository.
- Full restoration is journaled and resumable, not an atomic filesystem operation.
  Crash recovery is implemented; universal power-loss durability is not claimed.
- Linked worktrees, submodules, nested repositories, partial clones, sparse
  checkouts, alternate object stores, symlinked Git metadata, mounted subtrees,
  and special files are rejected. Windows supports ordinary local repositories; reparse points, junctions, and symlinks are rejected.
- File contents, ordinary permission bits, symlink targets, and empty directories
  are captured. Ownership, ACLs, extended attributes, timestamps, hard-link
  relationships, and setuid/setgid/sticky bits are not restored.
- Unsaved editor buffers, external symlink targets, remote changes, and side
  effects outside the repository (including hooks) are outside recovery scope.
- `push`, arbitrary Git aliases, Git global options, and repository-changing
  environment overrides are not accepted by the wrapper. Use ordinary Git for
  remote operations; a local restore cannot undo a remote push.


On Windows, the default store is `%LOCALAPPDATA%\Unspill` (or `~/AppData/Local/Unspill` if that variable is missing). Use a local NTFS volume with hard-link support. Directory fsync and POSIX permission preservation are unavailable on Windows; file bytes are flushed, but directory-entry power-loss durability is not guaranteed. Network shares and cloud-synced folders are not supported/tested storage locations.

[Back to the command reference](COMMANDS.md) · [README](../README.md)
