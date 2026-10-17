# Changelog

## 0.4.0 — 2026-10-17 (Unspill public alpha)

- Rename the project, Python package, CLI, and standalone downloads to Unspill.
- Keep existing v1 histories readable, discover legacy default stores per repository,
  and accept BGIT_HOME as a fallback to UNSPILL_HOME.
- Refuse ambiguous dual default histories; never move, merge, or erase backups.
- Include migration instructions and a dated preliminary naming-screening record.
- Preserve Apache-2.0, authorship, third-party notices, and historical release tags.

Earlier versions below were released under the former name BGit.

## 0.3.0 — 2026-10-16 (public alpha)

- Descriptive checkpoints with branch, commit subject, changed paths, stash names,
  and separately recorded command outcomes.
- Stable `@N` selectors, timeline search, file history and text comparisons.
- Guided terminal recovery and previews against the current workspace.
- Compatibility with existing v1 snapshots without fabricated context.
- Native Windows support and a Windows/macOS/Linux Python 3.11–3.14 CI matrix.
- Standalone executable builds for Windows x64, macOS Intel/Apple Silicon,
  and Linux x64; pipx installation instructions.
- Shorter README linked to installation, command, storage, and testing guides.
- 115 tests and an opt-in real public repository recovery demonstration.


## 0.1.0 — 2026-10-16 (public alpha)

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
run on a remote service at the time of preparation. Building and installing the
package in an isolated Python 3.12 environment and running the installed `bgit`
command were also validated.

The source repository is https://github.com/Qwin/BGit under Robert Al-Malak's
personal account. This version is not published to a package registry. See the README for
the supported layouts and explicit limitations before using it with real work.
