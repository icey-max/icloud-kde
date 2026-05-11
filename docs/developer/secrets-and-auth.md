# Secrets and Auth Contract

## Secret storage contract

The daemon represents credential and session material with secret references.
Project-owned config files store paths and tuning only; they do not store raw
credential values.

Secret service namespace:

- `org.kde.ICloudDrive`

Secret kinds:

- `apple_id_password` - Apple ID password material used only to create a
  pyicloud session.
- `pyicloud_session` - pyicloud session material owned by the daemon/backend
  adapter.
- `trust_metadata` - trusted-session or cookie-directory metadata migrated from
  legacy `icloud-linux` config.

KWallet helper command:

- `icloud-kde-secret-tool status`
- `icloud-kde-secret-tool store --account <label> --kind <kind>`
- `icloud-kde-secret-tool lookup --account <label> --kind <kind>`
- `icloud-kde-secret-tool delete --account <label> --kind <kind>`

The `store` command receives the secret value on stdin. Secret values must not be
provided as command-line arguments, written into daemon JSON, or returned in
status payloads.

## Plaintext migration

Legacy `icloud-linux` config can contain plaintext `username`, `password`, and
`cookie_dir` values. Phase 3 migration reads only top-level scalar keys from the
legacy YAML-like file, then either:

- migrates eligible material into KWallet or a compatible secret-service backend,
  or
- invalidates the legacy plaintext material if no compatible secret backend is
  available.

Migration renames the original file to a timestamped backup ending
`.icloud-kde-migrated.bak`, writes a replacement with
`# migrated to KWallet/Secret Service by icloud-kde`, and removes the legacy
plaintext credential/session keys from the replacement. The replacement is not a
project-owned daemon config file; it is only a redacted legacy marker.

Project-owned daemon config remains non-secret. `DaemonConfig` must not gain
fields for Apple ID passwords, tokens, cookies, sessions, or secret values.

## Auth controller contract

The auth controller consumes secret references and returns project-owned auth
status DTOs. `BeginSignIn` uses a password secret reference rather than a raw
password argument. Two-factor and two-step verification codes are short-lived UI
inputs; they must not be persisted, logged, or returned in status payloads.
