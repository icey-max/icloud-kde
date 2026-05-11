# Filesystem Semantics

This document defines the v1 local sync-root filesystem contract.

## Supported In v1

v1 supports ordinary files and folders.

Regular files and directories are the only supported round-tripped local entry
types. Size and timestamp metadata are treated as best-effort sync metadata.

## Unsupported In v1

Symlinks are not round-tripped as symlinks in v1.

Sockets, devices, FIFOs, and unknown local filesystem entry types are
unsupported for v1 sync. Ownership, ACLs, xattrs, and full POSIX mode fidelity are not v1 guarantees.

## State Reporting

Unsupported entries are reported as unsupported problem items.

The daemon reports these entries with `kind` set to `unsupported_file_type`,
`severity` set to `warning`, `state` set to `unsupported`, and a POSIX-style
sync-root-relative path such as `/docs/link`.

## FUSE Behavior

The inherited FUSE layer rejects non-regular special-file creation through
`mknod()` with `ENOSYS`. Regular file and folder operations remain the supported
v1 path for local applications.

## Testing Matrix

- Regular files are classified as supported.
- Directories are classified as supported.
- Symlinks are classified with `lstat()` and are not followed.
- FIFOs are classified as unsupported.
- Unsupported scan results use POSIX-style paths beginning with `/`.
