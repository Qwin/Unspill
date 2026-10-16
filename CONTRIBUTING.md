# Contributing

Use Python 3.11+ and Git. Run `python3 -m unittest discover -v` before submitting a
change. Tests must use temporary repositories, isolate Git configuration, and
never access the network or modify the contributor's real repositories.

Keep storage, repository orchestration, and CLI responsibilities separate. Prefer
the standard library and small, explicit functions. Never introduce automatic
history deletion or make local recovery depend on a service.

For each recovery feature, test the destructive action against real Git, then
assert restored working contents, index state, and refs as appropriate. Include a
failure-path test proving that unsuccessful backup prevents destruction. Avoid
tests that merely restate an implementation detail.

Document every change to capture scope, filesystem support, the storage format,
or recovery guarantees. An unsupported layout should fail explicitly rather than
silently receive partial protection. Changes to the storage format require a
version and a migration/recovery plan for existing backups.

Contributions are accepted under Apache-2.0, the same license as this project.
Do not copy third-party code without checking compatibility and preserving all
required notices. No contributor license agreement is currently required.
