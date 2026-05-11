# Sync Invariants

Phase 1 treats these sync behaviors as compatibility invariants. Later daemon,
KDE, KIO, notification, and packaging work should preserve these behaviors
unless a future phase explicitly replans the sync model.

## Conflict Preservation

Conflict copies preserve local data when local and remote state diverge. A
conflict copy must clear backend identity fields such as drive id, document id,
etag, zone, share id, and synced path, then remain dirty so the sync engine can
upload or otherwise surface the preserved local content.

Silent last-writer-wins behavior is not acceptable for v1.

## Retry And Backoff

Background hydration failures use exponential backoff capped at 300 seconds.
The current inherited retry sequence starts at 5 seconds and doubles until it
reaches the cap.

Auth-required failures are not treated like ordinary retryable network errors.
They should surface as auth-required state in later daemon and KDE phases.

## Concurrency

Download concurrency defaults to a single pyicloud session at a time. The
inherited engine may allow a warmup worker pool, but remote downloads pass
through a one-at-a-time semaphore because iCloud web access is sensitive to
aggressive concurrent use.

Later tuning UI must keep conservative defaults and make risk visible.

## Hydration And Persistent Cache

Hydration-on-open remains part of the sync contract: opening an unhydrated file
should hydrate it before serving local bytes. Persistent cache recovery should
reuse existing state and should not convert placeholders into hydrated content
unless real local bytes exist.

Crash-recovery-relevant state lives in the SQLite sync state and local mirror.
Future refactors should preserve durable identity, dirty, tombstone, hydrated,
local checksum, and synced-path semantics.

## Local Rename Tracking

Local renames keep the previous synced path and mark the renamed root entry
dirty. This gives the upload/reconcile path enough information to perform a
backend rename or preserve the local change instead of treating the renamed
file as unrelated content.

## Remote Delete Of Dirty Local Content

If remote metadata no longer contains an item while the local entry is dirty,
the engine must preserve the local content as an upload candidate. The local
entry should clear remote identity and remain dirty instead of deleting the
local file.

## Shared Metadata

Shared metadata, including share ids, must round-trip through sync state and
adapter DTOs. Shared item identity is part of backend compatibility because
the inherited engine reconstructs backend nodes from persisted metadata.

## Filesystem Semantics

The user-visible sync root supports ordinary regular files and folders in v1.
Unsupported Unix semantics such as symlinks, sockets, devices, FIFOs, ownership,
ACLs, xattrs, and full mode fidelity are defined in
[filesystem-semantics.md](filesystem-semantics.md). Unsupported local entries
must be rejected by the filesystem layer or surfaced as daemon problem items.

## Fixture Policy

Fixtures must be sanitized. In operational terms, fixtures must be sanitized.
They must not include credentials, account
identifiers, tokens, cookies, personal filenames, shared-user details, or other
sensitive iCloud metadata. Prefer synthetic data for default tests.

## Live Test Policy

Default tests must not require an Apple account or live iCloud access. Live
tests are optional and skipped by default. In operational terms, live tests are optional and skipped by default. If live tests are added, they must be
guarded by explicit environment variables and must operate only on an isolated
test folder or account configuration.
