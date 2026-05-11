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
