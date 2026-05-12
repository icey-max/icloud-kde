# Daemon API Contract

Phase 2 defines the daemon-facing API that KDE clients consume. The daemon is
the source of truth for sync state; clients must not import Python sync
internals, query the state database directly, or parse logs for product state.

## D-Bus Identity

- Bus name: `org.kde.ICloudDrive`
- Object path: `/org/kde/ICloudDrive`
- Interface: `org.kde.ICloudDrive`

Payloads use dictionaries with string enum values so C++, QML, Python, and test
clients can consume the same contract.

## Methods

- `GetStatus() -> a{sv}`
- `GetItemState(s path) -> a{sv}`
- `ListProblemItems() -> aa{sv}`
- `Pause() -> a{sv}`
- `Resume() -> a{sv}`
- `RequestSync() -> a{sv}`
- `Hydrate(s path) -> a{sv}`
- `GetConfig() -> a{sv}`
- `SetSyncRoot(s path) -> a{sv}`

## Auth and recovery methods

- `GetAuthStatus() -> a{sv}`
- `BeginSignIn(s apple_id, s password_secret_ref) -> a{sv}`
- `SubmitTwoFactorCode(s code) -> a{sv}`
- `ListTrustedDevices() -> aa{sv}`
- `SendTwoStepCode(s device_id) -> a{sv}`
- `SubmitTwoStepCode(s device_id, s code) -> a{sv}`
- `RequestReauth() -> a{sv}`
- `CollectLogs(s destination) -> a{sv}`
- `RebuildCache(s confirm_token) -> a{sv}`
- `RevealSyncRoot() -> a{sv}`

`BeginSignIn` takes a password secret reference in the exact form
`org.kde.ICloudDrive:<account_label>:apple_id_password`. It does not accept a
raw password argument.

## Signals

- `StatusChanged(a{sv})`
- `ItemStateChanged(s path, a{sv} state)`
- `ProgressChanged(a{sv})`
- `ProblemRaised(a{sv})`
- `AuthStateChanged(a{sv})`
- `RecoveryActionCompleted(a{sv})`

## Service States

- `starting`
- `scanning`
- `idle`
- `syncing`
- `paused`
- `offline`
- `auth_required`
- `account_blocked`
- `web_access_blocked`
- `degraded`
- `stopping`

## Item States

- `hydrated`
- `placeholder`
- `dirty`
- `syncing`
- `conflicted`
- `offline`
- `auth_required`
- `unsupported`
- `error`

## Safe Controls Only

The daemon exposes status queries, non-destructive sync controls, and explicit
recovery actions. Cache rebuild is permitted only through `RebuildCache` with a
confirmation token; it moves the internal cache to a backup and must not delete
local files in the sync root.

Remote removal, local purge, account reset, force overwrite, and conflict
resolution are not part of this D-Bus contract.

## Boundary Rules

- API payloads are project-owned dictionaries or enum strings.
- Raw backend library objects must not cross this boundary.
- State database rows must not be treated as public API.
- Account auth blockers must stay distinguishable from generic offline state.

## Phase 4 Desktop Events

KDE notifier and file-manager clients derive desktop events only from the
existing daemon D-Bus surface:

- `GetStatus`
- `GetAuthStatus`
- `ListProblemItems`
- `GetItemState`
- `ProgressChanged`
- `ProblemRaised`
- safe controls: `Pause`, `Resume`, `RequestSync`, `Hydrate`,
  `RequestReauth`, and `RevealSyncRoot`

`ListProblemItems` can report `conflict`, `dirty`, `unsupported_file_type`,
`auth_required`, `account_blocked`, `web_access_blocked`, and `upload_stuck`
problem kinds. Upload-stuck state is daemon-owned state: KDE clients must not
infer it from local file timestamps, logs, SQLite rows, or sync-engine private
state.

Desktop clients must treat these payloads as user-visible copy constraints:
messages must not include Apple IDs, password references, cookies, tokens,
secret references, or full home paths. Notification and tray actions remain
non-destructive and map only to the safe controls listed above.

## Dolphin and file manager integration

Dolphin integration is daemon-backed and non-destructive. The Places helper
reads only `GetConfig` and uses the returned `sync_root` to maintain a local
folder entry named `iCloud Drive` through KDE Places APIs.

Dolphin right-click actions use only these daemon calls after canonical sync-root validation has accepted every selected local file URL:

- `GetStatus`
- `GetItemState`
- `ListProblemItems`
- `Pause`
- `Resume`
- `RevealSyncRoot`

The action plugin must return no iCloud Drive actions outside the configured
sync root. It must not parse daemon logs, read SQLite state, import Python sync
internals, or interpolate selected paths into shell commands. Conflict details
are informational only: the desktop surface preserves both versions and does
not resolve, overwrite, or remove either file.

## Baloo indexing boundary

Baloo integration consumes daemon `GetConfig` and `GetItemState` state through
the same desktop D-Bus boundary as the notifier and Dolphin actions. It does not
read SQLite state, daemon logs, backend cache contents, cookies, tokens, KWallet
material, or Python sync internals as indexing inputs.

Hydrated files in the configured sync root may be indexed by KDE search.
Remote-only placeholders are name-only until they download. This depends on the
filesystem placeholder policy: Baloo and KFileMetaData extractor reads for clean
remote-only placeholders do not hydrate files or expose remote-only bytes.

The desktop integration reports local indexing status only. It does not claim
server-side search, and it does not search remote-only file contents before the
file is hydrated locally.
