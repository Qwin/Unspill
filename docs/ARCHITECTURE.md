# Architecture and invariants

## Modules

- `storage.py`: SHA-256 object addressing, zlib compression, verification,
  fsynced JSON writes, and a per-repository advisory lock.
- `repository.py`: repository compatibility checks, filesystem inventory,
  snapshot manifests, protected commands, exports, and restore transactions.
- `cli.py`: argument parsing, timeline display, and user-facing errors.

## Capture

1. Acquire the external BGit store lock.
2. Reject unsupported repository layouts and Git locks.
3. Inventory the complete repository, including `.git`, without following symlinks.
4. Stream each regular file to a compressed temporary object, hash its original
   bytes, fsync, and publish by hard link if that hash is new. Verify reused objects.
5. Recheck file metadata and the complete inventory to detect concurrent changes.
6. Publish a versioned JSON manifest without replacing an existing snapshot.
7. Only then run the requested Git command.

Object contents are independent of Git's object lifecycle. Capturing the Git
directory preserves unreachable objects, the index, stashes, reflogs, refs, and
in-progress operation files. This deliberately favors correctness for ordinary
repositories over storage efficiency in monorepos. A Git repack may create a new
large file even when most underlying Git objects are unchanged.

There is no snapshot garbage collector. An interrupted capture may leave unused
objects, but cannot publish a completed manifest referencing a partially written
object. Inventory checks are not a filesystem snapshot primitive: external writers
must be paused. The public CLI owns locking; repository methods are internal and
assume the caller holds that lock for mutations, except initialization.

## Restore

1. Resolve an immutable manifest and validate paths and entry shapes.
2. Reconstruct and checksum the target in a staging directory outside the repo.
3. Capture the current repository as a new `before-restore` snapshot.
4. Durably write `pending.json` with target and rollback IDs.
5. Replace the repository contents from staging, without following symlinks.
6. Sync copied files/directories, append a completion event, and remove the journal.

If replacement fails, the journal and both snapshots remain. `resume` reconstructs
the requested state from the immutable store; `resume --rollback` reconstructs the
pre-restore state. Both can run with an explicit `--repo` even if `.git` was removed.
They are destructive to the partial tree, so no new work should be performed there
until recovery completes. Whole-tree replacement is not atomic and does not provide
a blanket power-failure guarantee across filesystems and hardware.

## Format v1

A snapshot includes `version`, `id`, UTC `created`, `label`, `kind`, optional
`source`, and an `entries` map keyed by repository-relative POSIX paths. Files
contain `type`, `mode`, `size`, and an object hash; directories contain `type` and
`mode`; symlinks contain `type`, `mode`, and `target`.

IDs contain a nanosecond-scale sequence plus a random suffix. While holding the
store lock, capture chooses a sequence greater than every previous snapshot and
at least the current clock value, so clock rollback cannot reorder the timeline.
The separate `created` timestamp records wall-clock UTC time.
File contents are streamed; path inventories and manifests are held in memory.

Restoration preserves regular permission bits (0777), not privileged mode bits.
Manifests are validated but not signed or separately checksummed. SHA-256 validates
object bytes against their content addresses. Backup stores are trusted local data.
