# BGit command reference

[README](../README.md) · [Installation](INSTALL.md) · [Storage and limitations](STORAGE.md)

BGit works in an existing Git repository. Run `bgit init` once, then use
`bgit git COMMAND` for automatic pre-operation checkpoints. Snapshots describe
the state **before** the action, not after it. Only captured work is recoverable.

## Commands at a glance

| Command | Purpose |
| --- | --- |
| `bgit init` | Capture an existing repository and start its recovery timeline |
| `bgit snapshot -m "Label"` | Make a named manual checkpoint |
| `bgit git COMMAND ...` | Checkpoint before a supported Git operation |
| `bgit timeline` | Show actions, times, branches, commit subjects and saved changes |
| `bgit history PATH` | Browse captured versions of a file |
| `bgit inspect SELECTOR` | Print a snapshot's full summary as JSON |
| `bgit diff SELECTOR --path PATH` | Compare the current file with its captured version |
| `bgit recover` | Open the guided terminal recovery picker |
| `bgit recover SELECTOR --to DIR` | Export a separate repository copy |
| `bgit recover SELECTOR --path PATH --to DIR` | Export a file or directory |
| `bgit restore SELECTOR --dry-run` | Preview the changes a full restoration would make |
| `bgit restore SELECTOR` | Restore the complete captured workspace and Git metadata |
| `bgit undo` | Restore the latest pre-command or pre-restore checkpoint |
| `bgit resume [--rollback]` | Finish or roll back an interrupted restore |
| `bgit verify` | Check manifests and all referenced object checksums |

`bgit --help` shows top-level help. `bgit COMMAND --help` explains BGit command
options. `bgit git COMMAND --help` passes help through to Git. `bgit --version`
prints the installed version.

## Choosing a checkpoint

Selectors accept a full snapshot ID, a unique ID prefix, or a numbered choice such
as `@18`. Numbers are assigned oldest-first across the complete timeline and stay
stable as new snapshots are added. Search results retain the original numbers.
Numbers are local to a repository; full IDs remain available for scripts.

Human-readable timelines show newest-first, with local timestamps including the
timezone. JSON timelines remain oldest-first and use the stored UTC timestamps.

```sh
bgit timeline
bgit timeline --search "login"
bgit timeline --branch feature/login
bgit timeline --branch feature/login --search "reset"
bgit timeline --json
bgit inspect @18
```

Illustrative output:

```text
#18  2026-10-16 10:42:00 MST  feature/login
  Before git reset --hard HEAD~2
  Commit: Add password validation [a12bc345]
  Saved: 1 staged, 2 unstaged, 1 untracked; 0 stashes
    MM src/login.py
     M src/errors.py
    ?? notes.txt
  Operation outcome: completed
  Select: @18  |  ID: <full-snapshot-id>
```

Staged and unstaged counts can overlap: `MM` means the same file has both kinds of
change. Unmerged paths can appear in both counts. Counts come from Git status;
ignored files are captured too, but are not included in these status counts.
The summary shows up to five changed paths and three stash names; `inspect`
includes the full captured context and all workspace paths.

Search matches labels and recorded Git context: branch, commit subject, changed
paths and stash names. It does not search file contents. Detached HEAD and unborn
branches have explicit labels. Older snapshots without descriptive metadata remain
recoverable and are labeled as legacy; BGit does not invent missing context.

Operation outcomes are appended separately so snapshot records stay immutable.
They distinguish completed, failed, and stopped-on-conflicts operations. If a
process was interrupted before it recorded the result, the outcome is unknown.
Descriptions retain recognized operation modes and valid commit/branch references;
they intentionally omit arbitrary command arguments such as credential-bearing
URLs and commit-message arguments. Existing commit subjects are captured locally.

## Guided recovery

```sh
bgit recover
```

In a terminal, choose the last operation, a file's history, branch/stash operations,
or the full timeline. Pick an `@number` from the displayed results. BGit previews
workspace changes, staging changes, and the captured branch/commit, then offers:

- `d`: inspect a file's text differences;
- `r`: restore the **whole checkpoint**, saving your current state first;
- `e`: export into a new folder (only the selected file when entering from file history);
- Enter or `q`: cancel without changing the repository.

Choosing a branch/stash operation selects a full repository checkpoint, not an
isolated branch or stash restore. Full restoration can also change unrelated files;
use a separate export when you want to inspect first.

The picker requires a terminal and holds the BGit lock while open. It does not lock
out editors or other Git clients; pause their writes while using it. For scripts,
use explicit `restore` or `recover SELECTOR --to DIR` commands instead.

## Preview and compare

```sh
bgit restore @18 --dry-run
bgit diff @18 --path src/login.py
```

The preview compares the selected checkpoint with the **current live workspace**.
It lists paths to recover, replace, or remove, plus whether the index/Git metadata
will change. It performs no restoration and creates no checkpoint. Previews hash
the current tree and can be slow in large repositories.

Text diffs run from **current -> checkpoint**: removed lines are current content
that restoration would replace; added lines are captured content that would return.
UTF-8 files up to 1 MiB receive unified diffs. Binary, large, directory, and symlink
entries receive a descriptive message instead. Text diffs do not show staging
differences; full restore preserves the captured index independently.

## File history

```sh
bgit history src/login.py
bgit history src/login.py --json
```

History shows captured content/type/permission transitions, collapsing adjacent
identical versions. An `absent` entry means the file was missing in that checkpoint.
This is snapshot history, not a record of every edit between captures. Paths are
exact and repository-relative; renames are not automatically followed.

## Full restore and undo

```sh
bgit restore @18 --dry-run
bgit restore @18
bgit undo
```

Explicit `restore` executes without an additional prompt. It first verifies and
stages the target, captures the current state, and then replaces the live workspace
and `.git`. This includes the index, refs, stash stack, reflogs, configuration,
hooks, and operation state. Files created after the selected checkpoint leave the
live tree, but remain in the pre-restore snapshot. Restoring does not delete later
snapshots and does not execute saved hooks; later Git commands can execute them.

`undo` picks the newest pre-command or pre-restore checkpoint. Running it twice
toggles back through the restoration; it does not progressively walk backward.
Use specific numbered choices to travel further back. Failed commands also retain
their checkpoint, since an unsuccessful Git operation may still modify files.

## Export without replacing current work

```sh
bgit recover @18 --path src/login.py --to ../rescued-file
bgit recover @18 --path src --to ../rescued-source
bgit recover @18 --to ../earlier-project
```

The first command writes `../rescued-file/src/login.py`. A full export includes
`.git`; a file/directory export does not. The destination must not already exist
and must be outside the repository and backup store. These commands do not alter
the live repository or add a checkpoint. A path absent from the snapshot cannot
be exported; choose an earlier checkpoint where it exists.

## Interrupted restoration

Stop other writers and do not edit the partial tree. If you already made new edits
after the interruption, copy them elsewhere before resuming: resume does not make
a new checkpoint of an incomplete repository.

```sh
bgit --repo /absolute/path/to/project resume
bgit --repo /absolute/path/to/project resume --rollback
```

The first finishes the recorded target; the second restores the pre-restore
checkpoint. Both replace the partial tree. Explicit `--repo` allows recovery even
if `.git` is incomplete. The root directory must still exist.

`--repo PATH` is a global option and comes before the command. Without it, commands
discover the repository from the current directory. Git arguments retain their
usual directory-relative meaning; BGit file-history/export paths are root-relative.

## Verification

```sh
bgit verify
```

Verifies snapshot structure and referenced compressed objects against SHA-256
hashes. This detects damage but cannot repair it without another backup. Manifests
are not cryptographically authenticated. Preview is not a substitute for verify.

## Supported Git commands

Protected: `add`, `am`, `apply`, `branch`, `checkout`, `cherry-pick`, `clean`,
`commit`, `fetch`, `gc`, `merge`, `mv`, `pull`, `rebase`, `reset`, `restore`,
`revert`, `rm`, `stash`, `switch`, `tag`.

Inspection pass-through: `diff`, `log`, `show`, `status`.

Always use `bgit git COMMAND` to avoid ambiguity. `bgit restore` and `bgit diff`
refer to BGit checkpoints; `bgit git restore` and `bgit git diff` invoke Git.
Non-conflicting shorthands such as `bgit reset --hard` also work.

Git global options, arbitrary aliases, `push`, and environment variables that
redirect Git's repository/index/object store are rejected. Use ordinary Git for
remote pushes; a local restore cannot undo changes already published remotely.
The wrapper returns Git's exit code. BGit errors return 1; invalid CLI syntax
returns 2; Ctrl-C returns 130.
