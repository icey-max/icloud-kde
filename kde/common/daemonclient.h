#pragma once

#include <QObject>
#include <QTimer>
#include <QVariantList>
#include <QVariantMap>

class DaemonClient : public QObject
{
    Q_OBJECT

public:
    struct Snapshot {
        QVariantMap serviceStatus;
        QVariantMap authStatus;
        QVariantMap config;
        QVariantList problemItems;

        bool operator==(const Snapshot &other) const;
        bool operator!=(const Snapshot &other) const;
    };

    explicit DaemonClient(QObject *parent = nullptr);

    QVariantMap serviceStatus() const;
    QVariantMap authStatus() const;
    QVariantMap config() const;
    QVariantList problemItems() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantMap getItemState(const QString &path);
    Q_INVOKABLE QVariantMap pause();
    Q_INVOKABLE QVariantMap resume();
    Q_INVOKABLE QVariantMap requestSync();
    Q_INVOKABLE QVariantMap hydrate(const QString &path);
    Q_INVOKABLE QVariantMap requestReauth();
    Q_INVOKABLE QVariantMap revealSyncRoot();

    void startPolling(int intervalMs = 30000);
    void stopPolling();
    bool isPolling() const;

Q_SIGNALS:
    void serviceStatusChanged(const QVariantMap &status);
    void authStatusChanged(const QVariantMap &status);
    void configChanged(const QVariantMap &config);
    void problemItemsChanged(const QVariantList &problemItems);
    void itemStateChanged(const QString &path, const QVariantMap &state);
    void progressChanged(const QVariantMap &progress);
    void problemRaised(const QVariantMap &problem);
    void recoveryActionCompleted(const QVariantMap &result);
    void snapshotChanged(const DaemonClient::Snapshot &snapshot);

private Q_SLOTS:
    void pollSnapshots();
    void onStatusChanged(const QVariantMap &status);
    void onItemStateChanged(const QString &path, const QVariantMap &state);
    void onProgressChanged(const QVariantMap &progress);
    void onProblemRaised(const QVariantMap &problem);
    void onAuthStateChanged(const QVariantMap &status);
    void onRecoveryActionCompleted(const QVariantMap &result);

private:
    void subscribeToSignals();
    Snapshot fetchSnapshot() const;
    void applySnapshot(const Snapshot &snapshot, bool forceSignals);
    QVariantMap callMap(const QString &method, const QVariantList &args = {}) const;
    QVariantList callList(const QString &method, const QVariantList &args = {}) const;

    Snapshot m_snapshot;
    QTimer m_pollTimer;
};
