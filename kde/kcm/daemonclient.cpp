#include "daemonclient.h"

#include <QDBusInterface>
#include <QDBusReply>

namespace
{
constexpr const char *BusName = "org.kde.ICloudDrive";
constexpr const char *ObjectPath = "/org/kde/ICloudDrive";
constexpr const char *InterfaceName = "org.kde.ICloudDrive";
}

DaemonClient::DaemonClient(QObject *parent)
    : QObject(parent)
{
    refresh();
}

QVariantMap DaemonClient::authStatus() const
{
    return m_authStatus;
}

QVariantMap DaemonClient::serviceStatus() const
{
    return m_serviceStatus;
}

QVariantMap DaemonClient::config() const
{
    return m_config;
}

QVariantList DaemonClient::problemItems() const
{
    return m_problemItems;
}

bool DaemonClient::busy() const
{
    return m_busy;
}

void DaemonClient::refresh()
{
    setBusy(true);
    m_serviceStatus = callMap(QStringLiteral("GetStatus"));
    Q_EMIT serviceStatusChanged();
    m_config = callMap(QStringLiteral("GetConfig"));
    Q_EMIT configChanged();
    m_authStatus = callMap(QStringLiteral("GetAuthStatus"));
    Q_EMIT authStatusChanged();
    m_problemItems = callList(QStringLiteral("ListProblemItems"));
    Q_EMIT problemItemsChanged();
    setBusy(false);
}

void DaemonClient::beginSignIn(const QString &appleId, const QString &passwordSecretRef)
{
    m_authStatus = callMap(QStringLiteral("BeginSignIn"), {appleId, passwordSecretRef});
    Q_EMIT authStatusChanged();
}

void DaemonClient::submitTwoFactorCode(const QString &code)
{
    m_authStatus = callMap(QStringLiteral("SubmitTwoFactorCode"), {code});
    Q_EMIT authStatusChanged();
}

QVariantList DaemonClient::listTrustedDevices()
{
    m_problemItems = callList(QStringLiteral("ListTrustedDevices"));
    return m_problemItems;
}

void DaemonClient::sendTwoStepCode(const QString &deviceId)
{
    m_authStatus = callMap(QStringLiteral("SendTwoStepCode"), {deviceId});
    Q_EMIT authStatusChanged();
}

void DaemonClient::submitTwoStepCode(const QString &deviceId, const QString &code)
{
    m_authStatus = callMap(QStringLiteral("SubmitTwoStepCode"), {deviceId, code});
    Q_EMIT authStatusChanged();
}

void DaemonClient::setSyncRoot(const QString &path)
{
    m_config = callMap(QStringLiteral("SetSyncRoot"), {path});
    Q_EMIT configChanged();
}

void DaemonClient::requestReauth()
{
    callMap(QStringLiteral("RequestReauth"));
    refresh();
}

void DaemonClient::collectLogs(const QString &destination)
{
    callMap(QStringLiteral("CollectLogs"), {destination});
}

void DaemonClient::rebuildCache(const QString &confirmToken)
{
    callMap(QStringLiteral("RebuildCache"), {confirmToken});
}

void DaemonClient::revealSyncRoot()
{
    callMap(QStringLiteral("RevealSyncRoot"));
}

QVariantMap DaemonClient::callMap(const QString &method, const QVariantList &args)
{
    QDBusInterface iface(QString::fromLatin1(BusName),
                         QString::fromLatin1(ObjectPath),
                         QString::fromLatin1(InterfaceName));
    QDBusReply<QVariantMap> reply = iface.callWithArgumentList(QDBus::Block, method, args);
    return reply.isValid() ? reply.value() : QVariantMap {};
}

QVariantList DaemonClient::callList(const QString &method, const QVariantList &args)
{
    QDBusInterface iface(QString::fromLatin1(BusName),
                         QString::fromLatin1(ObjectPath),
                         QString::fromLatin1(InterfaceName));
    QDBusReply<QVariantList> reply = iface.callWithArgumentList(QDBus::Block, method, args);
    return reply.isValid() ? reply.value() : QVariantList {};
}

void DaemonClient::setBusy(bool busy)
{
    if (m_busy == busy) {
        return;
    }
    m_busy = busy;
    Q_EMIT busyChanged();
}
