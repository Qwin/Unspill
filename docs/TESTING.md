# Testing recovery

Run `python3 -m unittest discover -v` from the repository root with Python 3.11+.
No test dependencies, external accounts, credentials, or network are required.

The suite includes 122 tests across these layers:

| Layer | Coverage |
| --- | --- |
| Rename compatibility | Legacy stores and environment settings, precedence, ambiguity rejection, unchanged historical manifests, recovery after upgrade |
| Storage unit tests | Binary/empty objects, deduplication, compression, checksum failures, truncation, trailing bytes, path validation, immutable writes, exclusive locks, cleanup after failure |
| Real-Git integration | Hard reset, partial staging, clean including ignored files, stash clear followed by pruning, branch deletion, detached HEAD, rebase, conflict index state, reversible restore, exports, file types and permissions |
| Navigation and guided recovery | Descriptive context, stable selectors, search, legacy snapshots, previews, file history, text diffs, cancellation, export and restoration |
| CLI subprocess tests | Help, version, JSON timeline, named snapshots, preview, reset/undo, command ambiguity, exit codes, verification, export, explicit roots, relative paths |

Fault injection covers failed object writes, concurrent file creation, corrupt
objects, and interrupted restore with missing `.git`. Tests assert that unsafe
commands do not run after failed checkpoints, and that old snapshot bytes remain
unchanged after time travel. Every test uses its own temporary repository and
backup store, ignores the user's Git config, and supplies a test-only identity.

The example script is also a reproducible manual acceptance test:

```sh
python3 examples/recovery_demo.py
```

CI runs Windows, macOS, and Linux across Python 3.11–3.14. Platform-specific
filesystem tests are skipped where their semantics do not apply. The separate
binary workflow builds four native executables, runs CLI subprocess tests against
each executable, and exercises the synthetic recovery demo.

For an opt-in network test against a real public repository:

```sh
python3 examples/real_repository_demo.py --directory /path/to/new-test-directory
```

This clones `octocat/Hello-World` and makes only local disposable changes. It checks
hard-reset recovery of staged and unstaged edits, clean recovery of binary and
ignored files, stash deletion, local branch/commit recovery, retained history,
and backup verification. It never pushes. A local run against commit
`7fd1a60b01f91b314f59955a4e4d4e80d8edf11d` passed all six scenarios, preserving
11 checkpoints and verifying 60 unique objects with the navigation update.

Before production readiness, add filesystem-level power-loss testing, permission
and disk-exhaustion tests on multiple filesystems, property-based state sequences,
large-repository performance testing, and an independent recovery/security review.
