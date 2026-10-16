# Security and data handling

BGit is a local alpha. Its backup store is trusted local data, not a format for
importing snapshots from strangers. It can contain source code, credentials,
ignored files, historical secrets, Git configuration, and executable Git hooks.
Treat store access as access to all of that data. Restore only your own snapshots.

On POSIX, BGit creates its repository-specific store with mode 0700. Windows
stores inherit ACLs from their parent directory; Python mode bits do not provide
equivalent access control. Use a private user directory. File objects and JSON
records use private temporary files. It does not encrypt, upload, or automatically
expire backups. Object checksums detect accidental corruption, not malicious
rewriting of both manifests and objects. A process running as your user can modify
or remove the store. Use independent encrypted backups where appropriate.

This first release does not provide selective erasure of captured secrets. If a
secret is captured, rotate it and follow your organization's data-retention rules.
Do not enable BGit where its permanent local capture conflicts with those rules.

Repository contents must remain quiescent during capture and restore. Filesystem
checks reduce common races; they are not a sandbox against a hostile process
modifying the repository concurrently. Git commands can invoke user-configured
hooks, filters, merge tools, and other executables. BGit cannot reverse their
effects outside the repository.

Report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/Qwin/BGit/security/advisories/new).
Private reporting is enabled for this repository. Do not publish secrets or real
backup archives in public issues.
