# BGit

**Keep your work recoverable before you commit.**

BGit adds a local recovery timeline to an ordinary Git repository. It checkpoints
your workspace before supported Git commands, including staged changes, unstaged
edits, untracked files, ignored files, branches, stashes, and Git metadata.

```text
$ bgit git reset --hard
BGit checkpoint: <snapshot-id>
HEAD is now at ...

$ bgit undo
Restored latest pre-operation state. Undo this restore with <new-snapshot-id>

# Your staged and unstaged versions are back, separately.
```

**Alpha software for macOS and Linux.** Try the isolated demo first. This release
supports ordinary, self-contained Git repositories and requires exclusive access
while capturing or restoring. It is not yet a production backup service.

## Why BGit?

Git records commits. BGit also records the work you haven't committed.

| Accident | Recovery |
| --- | --- |
| Hard reset discarded your edits | `bgit undo` restores working files and the index |
| Clean deleted untracked or ignored files | Restore their captured contents |
| Stash clear removed the entire stack | Restore the stash refs, reflogs, and objects |
| Rebase rewrote the wrong history | Restore the pre-rebase repository |
| Merge abort discarded conflict work | Restore conflict files and index stages |
| Branch deletion lost a branch tip | Restore the captured reference and objects |
| You restored the wrong snapshot | Undo the restoration, or choose any older snapshot |

**Existing history is never discarded by BGit's normal operations.** Restoring
an old state creates a new checkpoint; all later snapshots remain available.
There is no automatic expiry, pruning, quota eviction, or snapshot deletion command.
This is retention, not protection against a failed disk or manual deletion of the
backup store. Keep a separate backup of the store for those failures.

## Install

Requirements: Python **3.11+**, Git on `PATH`, and macOS or Linux.
The runtime has no third-party Python dependencies. Setuptools is used for packaging.

From this checkout, install into a virtual environment **outside the repositories
you will protect**:

```sh
python3 -m venv "$HOME/.venvs/bgit"
"$HOME/.venvs/bgit/bin/python" -m pip install .
export PATH="$HOME/.venvs/bgit/bin:$PATH"
bgit --version
```

For development, use `pip install -e .`, or run `python3 -m bgit` from this checkout.
The project has not been published to a package registry; the package name is not
claimed by this repository.

## Watch it recover real mistakes

Run the self-contained demo from this checkout. No installation is required:

```sh
python3 examples/recovery_demo.py
```

The demo creates a fresh temporary repository and a separate backup directory. It
uses an isolated Git configuration and never touches your existing repositories.
It deliberately performs a hard reset, deletes untracked and ignored files, clears
a stash, and recovers each state with assertions. It prints the directory at the
start and leaves it available for inspection.

Expected highlights (IDs vary):

```text
PASS: hard reset recovered staged and unstaged versions
PASS: clean recovered untracked and ignored files
PASS: stash clear recovered the stash
PASS: restoring the past retained later history
Verified ... snapshots and ... unique objects.
```

## Everyday usage

In an existing Git repository:

```sh
bgit init
bgit snapshot -m "Before experimenting"
bgit git rebase main
bgit git reset --hard HEAD~1
bgit timeline
bgit undo
```

Use `bgit git <command>` for protected Git operations. Some commands also have a
shorthand, such as `bgit reset --hard`. **`bgit restore` restores a BGit snapshot;
`bgit git restore` runs Git's file-discard command.**

BGit runs your installed Git with its normal arguments, input/output, hooks, and
configuration. Automatic Git maintenance is disabled for the wrapped invocation.
Your repository format, remotes, and teammates' workflows stay ordinary Git.
BGit itself does not upload backups or require an account.

## Recovery recipes

### Undo the latest protected operation

```sh
bgit undo
```

This restores the most recent pre-command or pre-restore checkpoint. Running it
again reverses that restoration; it does **not** walk progressively backward.
Use explicit snapshot IDs to travel further back. Failed Git commands also retain
their checkpoint, because failed operations may still have changed files.

### Travel to a specific snapshot

```sh
bgit timeline
bgit inspect SNAPSHOT_ID
bgit restore SNAPSHOT_ID --dry-run
bgit restore SNAPSHOT_ID
```

Use an ID from the timeline or a unique ID prefix. The preview lists captured paths
and counts, not a textual diff. Restoration replaces the full workspace and `.git`
metadata. Files added after the selected snapshot are removed from the live tree,
but preserved in the automatically created pre-restore checkpoint.

The restored metadata includes the index, branch refs, stashes, reflogs, local Git
configuration, and hooks. Restores do not run hooks, but later Git commands can.

### Recover one file without replacing your current work

```sh
bgit recover SNAPSHOT_ID --path src/login.py --to ../rescued-file
```

The file appears at `../rescued-file/src/login.py`. The live repository is untouched.
You can also select a directory. Paths are relative to the repository root.
The destination must not already exist and must be outside the repository and store.

### Open a complete copy of the past

```sh
bgit recover SNAPSHOT_ID --to ../yesterdays-project
```

The result contains the captured workspace and `.git` directory. This provides a
separate place to inspect or continue an experiment without changing the original.

### Recover after an interrupted restore

Stop editors, Git clients, and other writers. Do not make further edits in the
partially restored repository. Use an explicit root path if `.git` is incomplete:

```sh
bgit --repo /absolute/path/to/project resume
# Or restore the checkpoint from immediately before the interrupted restore:
bgit --repo /absolute/path/to/project resume --rollback
```

Both commands replace the partial tree. Any new edits made after the interruption
are not automatically saved by `resume`; copy those elsewhere first.

### Check the backup store

```sh
bgit verify
bgit timeline --json
```

Verification validates manifests and checks all referenced object hashes. It
detects missing or damaged contents; it cannot repair a damaged backup without
another copy. Manifests are not cryptographically authenticated.

## Where history lives

Default location:

```text
~/.local/share/bgit/repositories/<hash-of-absolute-repository-path>/
  repository.json
  snapshots/       # Append-only snapshot manifests
  objects/         # Compressed, SHA-256-addressed file contents
  events/          # Restore completion records
  pending.json     # Present only during an unfinished restore
  lock
```

Set `BGIT_HOME` to select a different external location **before initialization**,
and use the same setting for later commands:

```sh
export BGIT_HOME=/path/outside/your/projects/bgit-data
bgit init
```

An in-project `.bgit` folder could be removed by `git clean -fdx`. BGit therefore
refuses stores inside the repository or stores containing the repository.
Unchanged contents share one object; snapshots do not duplicate every file's bytes.
Each snapshot still scans all files. Large repositories and changing Git packfiles
can be expensive. Keep sufficient disk space for backups **and restore staging**.

Repositories are identified by canonical absolute path in v0.1. Moving one does
not automatically reconnect its history. Keep the original store and use the old
root path to recover/export; relocation support is planned.

## Protection boundaries

- Only captured states are recoverable. Ordinary `git` commands, IDE actions, and
  edits do not create checkpoints automatically. There is no background watcher.
- **All files are included, even ignored files**, to recover from `clean -fdx`.
  This includes `.env`, credentials, generated output, and dependency directories.
  Backups are local with a private store directory, but are **not encrypted**.
  There are no exclusion rules in v0.1; do not use it where permanent capture of
  these files is unacceptable. Removing a secret from Git does not remove it here.
- Stop concurrent Git processes, builds, editors that save, and other writers
  during operations. BGit locks other BGit processes, rejects existing Git locks,
  and detects common capture races. It cannot freeze arbitrary processes or
  guarantee a consistent capture while external writers are active.
- If checkpoint creation fails, the protected command does not run. Restore
  verifies and stages target contents before changing the live repository.
- Full restoration is journaled and resumable, not an atomic filesystem operation.
  Crash recovery is implemented; universal power-loss durability is not claimed.
- Linked worktrees, submodules, nested repositories, partial clones, sparse
  checkouts, alternate object stores, symlinked Git metadata, mounted subtrees,
  and special files are rejected. Windows is not supported yet.
- File contents, ordinary permission bits, symlink targets, and empty directories
  are captured. Ownership, ACLs, extended attributes, timestamps, hard-link
  relationships, and setuid/setgid/sticky bits are not restored.
- Unsaved editor buffers, external symlink targets, remote changes, and side
  effects outside the repository (including hooks) are outside recovery scope.
- `push`, arbitrary Git aliases, Git global options, and repository-changing
  environment overrides are not accepted by the wrapper. Use ordinary Git for
  remote operations; a local restore cannot undo a remote push.

Protected commands: `add`, `am`, `apply`, `branch`, `checkout`, `cherry-pick`,
`clean`, `commit`, `fetch`, `gc`, `merge`, `mv`, `pull`, `rebase`, `reset`,
`restore`, `revert`, `rm`, `stash`, `switch`, `tag`.

Pass-through inspection commands: `diff`, `log`, `show`, `status`.

## Tests and development

```sh
python3 -m unittest discover -v
python3 examples/recovery_demo.py
```

The standard-library test suite includes storage unit tests, real-Git recovery
integration tests, and subprocess CLI tests. It uses temporary repositories,
isolated Git config, and no network. See [the testing guide](docs/TESTING.md).
CI is configured to run the suite on macOS and Linux with Python 3.11–3.14.

See [architecture](docs/ARCHITECTURE.md), [roadmap](docs/ROADMAP.md),
[contributing](CONTRIBUTING.md), and [security considerations](SECURITY.md).

## License and business model

The local engine is licensed under [Apache-2.0](LICENSE), a permissive open-source
license that allows commercial use and includes an express patent grant.
Paid hosted backup, support, and team services can be offered alongside this code.
The license also permits others to offer commercial products; it does not reserve
exclusive monetization rights for BGit's maintainers.

Local recovery is implemented entirely in this repository and has no paid gate.
This release uses original implementation code and Python's standard library;
Git is invoked as an external program, not bundled. See [third-party notes](THIRD_PARTY.md).
