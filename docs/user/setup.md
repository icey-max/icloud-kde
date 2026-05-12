# iCloud Drive Setup

## Open the iCloud Drive settings module

Open the KDE settings module from System Settings, or run:

```bash
kcmshell6 kcm_icloud
```

The module is named `iCloud Drive`.

## Connect your Apple ID

Use the Account page to connect an Apple ID through the daemon auth flow. If
iCloud asks for two-factor or two-step verification, the settings module shows
the required code or trusted-device step and sends the result to the daemon.

Credentials and session material are stored in KWallet or a compatible
secret-service backend, not plaintext project config.

## Choose sync locations

Use the Sync page to select the local sync root, cache location, startup
behavior, warmup mode, concurrency, and pause-on-startup default. Keep
concurrency conservative unless testing shows the account and network tolerate
more parallel work.

The local sync root is the normal folder that applications should use for iCloud
Drive files.

## Dolphin Places entry

After setup creates or validates a sync root, Dolphin shows a Places entry for
the folder. The Places entry is named `iCloud Drive`, uses the `folder-cloud`
icon, and opens the local sync root. It is not an `icloud:/` browser; ordinary
applications should keep using the local folder path.

If the sync root changes, the desktop helper updates the Places entry to the new
folder. If the folder is temporarily unavailable, Dolphin shows its normal local
folder error while the status notifier and settings module carry recovery state.

## Dolphin right-click actions

Inside the configured sync root, Dolphin can show these iCloud Drive actions:

- `Open iCloud Folder`
- `Show iCloud Drive Status`
- `Pause iCloud Drive Sync`
- `Resume iCloud Drive Sync`
- `Show Conflict Details`

The actions are hidden outside the sync root. `Show iCloud Drive Status` shows
sync state for the selected file or a count summary for multiple selected
items. `Show Conflict Details` appears only for conflicted items and uses this
next step: Compare the conflict copy before deleting either version.

Conflict details preserve both versions. They do not resolve the conflict or
remove either file.

## Search indexing

Hydrated files in your iCloud Drive folder can appear in KDE search.

Remote-only placeholders are indexed by name only until they download.

KDE file indexing is disabled for this folder. You can still browse files in Dolphin.

Indexing status is unavailable. Check the sync folder in iCloud Drive settings.

KDE search uses local hydrated content only. It does not search remote-only file
contents before they download.

## Recover from common problems

Use the Recovery page to request re-authentication, reveal the local folder,
collect logs, or rebuild the cache.

Cache rebuild moves the internal cache to a backup and rebuilds it. It does not
delete local files in the sync folder.

## Privacy and security limits

iCloud web access or account security settings can block Linux access. Advanced Data Protection may limit what this integration can read.

This project cannot guarantee Apple service availability or undocumented
endpoint stability. Visible auth and recovery states are the source of truth
when the account needs attention.

## Phase 4 desktop smoke checks

Use these checks after installing the KDE desktop components:

1. Places entry opens the local sync root from Dolphin.
2. The notifier reacts to auth, paused, syncing, offline, and degraded states.
3. All seven notification events match their configured copy and safe actions.
4. Inside-root service actions appear in Dolphin.
5. outside-root service actions are absent in Dolphin.
6. conflicted items show conflict actions without destructive resolution.
7. `kcmshell6 kcm_icloud` still opens the iCloud Drive settings module.
