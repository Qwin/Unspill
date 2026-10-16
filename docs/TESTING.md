# Testing recovery

Run `python3 -m unittest discover -v` from the repository root with Python 3.11+.
No test dependencies, external accounts, credentials, or network are required.

The suite has three layers:

| Layer | Coverage |
| --- | --- |
| Storage unit tests | Binary/empty objects, deduplication, compression, checksum failures, truncation, trailing bytes, path validation, immutable writes, exclusive locks, cleanup after failure |
| Real-Git integration | Hard reset, partial staging, clean including ignored files, stash clear followed by pruning, branch deletion, detached HEAD, rebase, conflict index state, reversible restore, exports, file types and permissions |
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

CI defines macOS/Linux jobs across Python 3.11–3.14. A configured matrix is not a
claim that all platforms were exercised locally; see the release notes for actual
local validation.

Before production readiness, add filesystem-level power-loss testing, permission
and disk-exhaustion tests on multiple filesystems, property-based state sequences,
large-repository performance testing, and an independent recovery/security review.
