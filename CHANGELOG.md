# Changelog

## 0.1.0 — 2026-10-16 (local alpha)

Initial implementation of BGit's local recovery engine:

- Permanent, append-only snapshots outside the protected repository.
- Compressed and deduplicated content, including independent Git metadata.
- Checkpoints before supported Git commands; failed checkpoints block execution.
- Timeline, inspection, reversible restore, selective export, and verification.
- A restore journal for resuming or rolling back an interrupted restoration.
- An Apache-2.0 license, contributor guide, architecture notes, and recovery demo.
- 80 storage, real-Git integration, and CLI tests.

Locally validated on macOS with Python 3.14.4 and Python 3.12.2. The recovery demo
also passed on Python 3.14.4. The GitHub Actions matrix is configured but has not
run on a remote service. Package installation has not been validated locally
because the available Python environments do not contain the build dependency;
the module entry point is exercised by the CLI tests.

This version is not published to GitHub or a package registry. See the README for
the supported layouts and explicit limitations before using it with real work.
