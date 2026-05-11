# Backend Compatibility Policy

## Pinned Source

Phase 1 vendors `icloud-linux` from:

- Upstream: `https://github.com/IsmaeelAkram/icloud-linux.git`
- Commit: `6ddd487d92662ace68b1e977d10e0cbc1fcc1b8c`
- Default branch at import: `master`
- Import manifest: `vendor/icloud-linux-import.json`

The upstream repository has no license file in its root at the pinned commit. This project can use the import for local planning and compatibility work, but license due diligence is required before release packaging.

## Adapter Boundary Rule

The backend is fragile because it depends on undocumented consumer iCloud web behavior through pyicloud-style calls. Raw `pyicloud` objects must not cross the adapter boundary. Higher-level daemon, KDE, KIO, KWallet, Dolphin, and notification code must depend on project-owned adapter types only.

The adapter boundary must normalize:

- iCloud item identity fields such as drive ids, document ids, etags, zones, share ids, names, parent identity, size, timestamps, and item type.
- File operations such as list, metadata lookup, download, upload/update, folder creation, rename, move, delete/trash, and shared metadata.
- Session and backend failures such as auth-required, account/web-access blocked, throttled, transient network failure, not found, precondition/conflict, unsupported response, and contract mismatch.

## Backend Update Policy

Backend updates are never automatic. A backend update requires:

1. Updating `vendor/icloud-linux-import.json` with the new commit or local patch note.
2. Running the adapter contract tests.
3. Reviewing or refreshing sanitized fixtures when backend response shapes changed.
4. Recording a compatibility note that explains the observed behavior change.

Contract or fixture failures block release unless the incompatibility is explicitly accepted and documented.

## Fixture Policy

Fixtures must be sanitized before commit. They must not contain:

- Apple account identifiers.
- Credentials, tokens, cookies, or session material.
- Personal filenames, folder names, shared-user data, or other private iCloud metadata.

Prefer synthetic fixture data for default tests. If recorded data is required for drift detection, add a redaction step before the fixture is committed.

## Live Test Policy

Default tests must not require live iCloud access. Live tests are opt-in and must be skipped unless explicit environment variables are set. Live tests must use an isolated test folder or account configuration and must not operate on a user's real iCloud Drive tree.

## Release Blockers

The following block release:

- Missing license due diligence for vendored upstream source.
- Raw backend library objects escaping into daemon or KDE-facing APIs.
- Contract tests failing against the selected adapter.
- Fixtures containing credentials, tokens, cookies, account identifiers, or personal iCloud metadata.
- Unreviewed backend updates that change operation or metadata semantics.

