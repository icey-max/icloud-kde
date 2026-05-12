#include "daemonclient.h"

#include <QDBusConnection>
#include <QDBusInterface>
#include <QDBusReply>

namespace
{
constexpr const char *BusName = "org.kde.ICloudDrive";
constexpr const char *ObjectPath = "/org/kde/ICloudDrive";
constexpr const char *InterfaceName = "org.kde.ICloudDrive";
constexpr int MinimumPollingIntervalMs = 30000;
}

bool DaemonClient::Snapshot::operator==(const Snapshot &other) const
{
    return serviceStatus == other.serviceStatus && authStatus == other.authStatus && config == other.config
        && problemItems == other.problemItems;
}

bool DaemonClient::Snapshot::operator!=(const Snapshot &other) const
{
    return !(*this == other);
}

DaemonClient::DaemonClient(QObject *parent)
    : QObject(parent)
{
    m_pollTimer.setSingleShot(false);
    connect(&m_pollTimer, &QTimer::timeout, this, &DaemonClient::pollSnapshots);
    subscribeToSignals();
    refresh();
}

QVariantMap DaemonClient::serviceStatus() const
{
    return m_snapshot.serviceStatus;
}

QVariantMap DaemonClient::authStatus() const
{
    return m_snapshot.authStatus;
}

QVariantMap DaemonClient::config() const
{
    return m_snapshot.config;
}

QVariantList DaemonClient::problemItems() const
{
    return m_snapshot.problemItems;
}

void DaemonClient::refresh()
{
    applySnapshot(fetchSnapshot(), true);
}

QVariantMap DaemonClient::getItemState(const QString &path)
{
    return callMap(QStringLiteral("GetItemState"), {path});
}

QVariantMap DaemonClient::pause()
{
    const QVariantMap result = callMap(QStringLiteral("Pause"));
    refresh();
    return result;
}

QVariantMap DaemonClient::resume()
{
    const QVariantMap result = callMap(QStringLiteral("Resume"));
    refresh();
    return result;
}

QVariantMap DaemonClient::requestSync()
{
    const QVariantMap result = callMap(QStringLiteral("RequestSync"));
    refresh();
    return result;
}

QVariantMap DaemonClient::hydrate(const QString &path)
{
    return callMap(QStringLiteral("Hydrate"), {path});
}

QVariantMap DaemonClient::requestReauth()
{
    const QVariantMap result = callMap(QStringLiteral("RequestReauth"));
    refresh();
    return result;
}

QVariantMap DaemonClient::revealSyncRoot()
{
    return callMap(QStringLiteral("RevealSyncRoot"));
}

void DaemonClient::startPolling(int intervalMs)
{
    m_pollTimer.start(qMax(intervalMs, MinimumPollingIntervalMs));
}

void DaemonClient::stopPolling()
{
    m_pollTimer.stop();
}

bool DaemonClient::isPolling() const
{
    return m_pollTimer.isActive();
}

void DaemonClient::pollSnapshots()
{
    applySnapshot(fetchSnapshot(), false);
}

void DaemonClient::onStatusChanged(const QVariantMap &status)
{
    if (m_snapshot.serviceStatus == status) {
        return;
    }
    m_snapshot.serviceStatus = status;
    Q_EMIT serviceStatusChanged(m_snapshot.serviceStatus);
    Q_EMIT snapshotChanged(m_snapshot);
}

void DaemonClient::onItemStateChanged(const QString &path, const QVariantMap &state)
{
    Q_EMIT itemStateChanged(path, state);
}

void DaemonClient::onProgressChanged(const QVariantMap &progress)
{
    Q_EMIT progressChanged(progress);
}

void DaemonClient::onProblemRaised(const QVariantMap &problem)
{
    Q_EMIT problemRaised(problem);
}

void DaemonClient::onAuthStateChanged(const QVariantMap &status)
{
    if (m_snapshot.authStatus == status) {
        return;
    }
    m_snapshot.authStatus = status;
    Q_EMIT authStatusChanged(m_snapshot.authStatus);
    Q_EMIT snapshotChanged(m_snapshot);
}

void DaemonClient::onRecoveryActionCompleted(const QVariantMap &result)
{
    Q_EMIT recoveryActionCompleted(result);
}

void DaemonClient::subscribeToSignals()
{
    QDBusConnection::sessionBus().connect(QStringLiteral("org.kde.ICloudDrive"),
                                          QStringLiteral("/org/kde/ICloudDrive"),
                                          QStringLiteral("org.kde.ICloudDrive"),
                                          QStringLiteral("StatusChanged"),
                                          this,
                                          SLOT(onStatusChanged(QVariantMap)));
    QDBusConnection::sessionBus().connect(QString::fromLatin1(BusName),
                                          QString::fromLatin1(ObjectPath),
                                          QString::fromLatin1(InterfaceName),
                                          QStringLiteral("ItemStateChanged"),
                                          this,
                                          SLOT(onItemStateChanged(QString,QVariantMap)));
    QDBusConnection::sessionBus().connect(QString::fromLatin1(BusName),
                                          QString::fromLatin1(ObjectPath),
                                          QString::fromLatin1(InterfaceName),
                                          QStringLiteral("ProgressChanged"),
                                          this,
                                          SLOT(onProgressChanged(QVariantMap)));
    QDBusConnection::sessionBus().connect(QString::fromLatin1(BusName),
                                          QString::fromLatin1(ObjectPath),
                                          QString::fromLatin1(InterfaceName),
                                          QStringLiteral("ProblemRaised"),
                                          this,
                                          SLOT(onProblemRaised(QVariantMap)));
    QDBusConnection::sessionBus().connect(QString::fromLatin1(BusName),
                                          QString::fromLatin1(ObjectPath),
                                          QString::fromLatin1(InterfaceName),
                                          QStringLiteral("AuthStateChanged"),
                                          this,
                                          SLOT(onAuthStateChanged(QVariantMap)));
    QDBusConnection::sessionBus().connect(QString::fromLatin1(BusName),
                                          QString::fromLatin1(ObjectPath),
                                          QString::fromLatin1(InterfaceName),
                                          QStringLiteral("RecoveryActionCompleted"),
                                          this,
                                          SLOT(onRecoveryActionCompleted(QVariantMap)));
}

DaemonClient::Snapshot DaemonClient::fetchSnapshot() const
{
    return Snapshot {
        callMap(QStringLiteral("GetStatus")),
        callMap(QStringLiteral("GetAuthStatus")),
        callMap(QStringLiteral("GetConfig")),
        callList(QStringLiteral("ListProblemItems")),
    };
}

void DaemonClient::applySnapshot(const Snapshot &snapshot, bool forceSignals)
{
    if (!forceSignals && snapshot == m_snapshot) {
        return;
    }

    const bool serviceChanged = forceSignals || snapshot.serviceStatus != m_snapshot.serviceStatus;
    const bool authChanged = forceSignals || snapshot.authStatus != m_snapshot.authStatus;
    const bool configDidChange = forceSignals || snapshot.config != m_snapshot.config;
    const bool problemsChanged = forceSignals || snapshot.problemItems != m_snapshot.problemItems;

    m_snapshot = snapshot;

    if (serviceChanged) {
        Q_EMIT serviceStatusChanged(m_snapshot.serviceStatus);
    }
    if (authChanged) {
        Q_EMIT authStatusChanged(m_snapshot.authStatus);
    }
    if (configDidChange) {
        Q_EMIT configChanged(m_snapshot.config);
    }
    if (problemsChanged) {
        Q_EMIT problemItemsChanged(m_snapshot.problemItems);
    }
    Q_EMIT snapshotChanged(m_snapshot);
}

QVariantMap DaemonClient::callMap(const QString &method, const QVariantList &args) const
{
    QDBusInterface iface(QString::fromLatin1(BusName),
                         QString::fromLatin1(ObjectPath),
                         QString::fromLatin1(InterfaceName));
    QDBusReply<QVariantMap> reply = iface.callWithArgumentList(QDBus::Block, method, args);
    return reply.isValid() ? reply.value() : QVariantMap {};
}

QVariantList DaemonClient::callList(const QString &method, const QVariantList &args) const
{
    QDBusInterface iface(QString::fromLatin1(BusName),
                         QString::fromLatin1(ObjectPath),
                         QString::fromLatin1(InterfaceName));
    QDBusReply<QVariantList> reply = iface.callWithArgumentList(QDBus::Block, method, args);
    return reply.isValid() ? reply.value() : QVariantList {};
}
