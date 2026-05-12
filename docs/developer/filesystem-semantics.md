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

## Baloo Name-Only Placeholder Reads

Remote-only placeholders are indexed by name only until they download. Normal
user and application opens of a clean unhydrated file still hydrate the file
through `ensure_local_file`.

When a Baloo or KFileMetaData extraction process such as `baloo_file_extractor`
or `kfilemetadata` opens or reads a clean remote-only placeholder, the FUSE
layer does not hydrate it. `open()` succeeds and `read()` returns empty bytes,
leaving the state entry unhydrated. This process-name check is an indexing
behavior guard only, not an authorization boundary.

Dirty files are not treated as safe remote-only placeholders. If local dirty
content exists, extractor reads continue to return the local bytes rather than
discarding or replacing them.

## Testing Matrix

- Regular files are classified as supported.
- Directories are classified as supported.
- Symlinks are classified with `lstat()` and are not followed.
- FIFOs are classified as unsupported.
- Unsupported scan results use POSIX-style paths beginning with `/`.
- Baloo/KFileMetaData reads for clean remote-only placeholders do not hydrate
  content.
