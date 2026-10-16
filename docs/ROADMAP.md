# Roadmap

## Implemented in the current alpha

- Local immutable snapshots with no automatic expiry.
- Independent, compressed and deduplicated contents outside the repository.
- Protected Git commands, timeline, inspection, and backup verification.
- Full restoration with a pre-restore checkpoint and recovery journal.
- Export one file, a directory, or a complete snapshot into a new location.
- Recovery tests against real Git and storage/CLI tests.

- Windows support and native downloads for four platform/architecture targets.
- Descriptive timelines, stable numbered choices, search, text diffs, file history,
  restoration previews, and guided recovery.

## Reliability before wider adoption

- Independent review, power-failure testing, stronger transaction semantics.
- Repository relocation and portable store import support.
- Benchmarks and incremental capture for larger repositories.
- Checksum/authentication design for manifests and replicated backups.
- Explicit retention exceptions and a carefully reviewed secret-erasure workflow.
- Precise inclusion policies without silent protection gaps.

## Workflow expansion

- Linked worktrees, submodules, partial clones, sparse checkouts.
- A graphical timeline and natural-language time selection.
- Background snapshots and editor/agent checkpoints with explicit coverage status.
- In-place selective restore and named alternate histories.

## Optional commercial services

- Encrypted, off-device backup with explicit storage limits.
- Cross-machine recovery and managed team deployment.
- Organization policy, operational monitoring, hosting, and support.

These are ideas, not available features or promised delivery dates. Local recovery
must remain usable offline without a paid service.
