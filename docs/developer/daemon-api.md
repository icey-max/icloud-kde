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

Phase 2 exposes only status queries and non-destructive controls: pause,
resume, sync request, hydration request, problem listing, config read, and sync
root update after validation.

Remote removal, local purge, cache rebuild, account reset, force overwrite, and
conflict resolution are recovery features for later UI phases. They are not part
of this D-Bus contract.

## Boundary Rules

- API payloads are project-owned dictionaries or enum strings.
- Raw backend library objects must not cross this boundary.
- State database rows must not be treated as public API.
- Account auth blockers must stay distinguishable from generic offline state.
