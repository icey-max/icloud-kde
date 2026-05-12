#include "daemonclient.h"

#include <QDBusInterface>
#include <QDBusReply>
#include <QProcess>
#include <QStandardPaths>

namespace
{
constexpr const char *BusName = "org.kde.ICloudDrive";
constexpr const char *ObjectPath = "/org/kde/ICloudDrive";
constexpr const char *InterfaceName = "org.kde.ICloudDrive";
constexpr const char *DefaultAccountLabel = "default";
constexpr const char *PasswordKind = "apple_id_password";

QString passwordSecretRefFor(const QString &accountLabel)
{
    return QStringLiteral("%1:%2:%3").arg(
        QString::fromLatin1(BusName),
        accountLabel,
        QString::fromLatin1(PasswordKind));
}

QVariantMap authError(const QString &message)
{
    return QVariantMap {
        {QStringLiteral("state"), QStringLiteral("error")},
        {QStringLiteral("account_label"), QString::fromLatin1(DefaultAccountLabel)},
        {QStringLiteral("apple_id"), QString()},
        {QStringLiteral("problem_kind"), QStringLiteral("unknown")},
        {QStringLiteral("message"), message},
        {QStringLiteral("devices"), QVariantList {}},
    };
}
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
    setAuthStatus(callMap(QStringLiteral("GetAuthStatus")));
    m_problemItems = callList(QStringLiteral("ListProblemItems"));
    Q_EMIT problemItemsChanged();
    setBusy(false);
}

void DaemonClient::connectAccount(const QString &appleId, const QString &password)
{
    const QString trimmedAppleId = appleId.trimmed();
    if (trimmedAppleId.isEmpty()) {
        setAuthStatus(authError(QStringLiteral("Enter your Apple ID to connect iCloud Drive.")));
        return;
    }
    if (password.isEmpty()) {
        setAuthStatus(authError(QStringLiteral("Enter your Apple ID password to connect iCloud Drive.")));
        return;
    }

    setBusy(true);
    const QString helper = QStandardPaths::findExecutable(QStringLiteral("icloud-kde-secret-tool"));
    if (helper.isEmpty()) {
        setBusy(false);
        setAuthStatus(authError(QStringLiteral(
            "KWallet helper is not installed. Install icloud-kde-secret-tool, then try again.")));
        return;
    }

    QProcess process;
    process.start(helper,
                  QStringList {
                      QStringLiteral("store"),
                      QStringLiteral("--account"),
                      QString::fromLatin1(DefaultAccountLabel),
                      QStringLiteral("--kind"),
                      QString::fromLatin1(PasswordKind),
                  });
    if (!process.waitForStarted(5000)) {
        setBusy(false);
        setAuthStatus(authError(QStringLiteral("Could not start the KWallet helper.")));
        return;
    }

    QByteArray passwordBytes = password.toUtf8();
    process.write(passwordBytes);
    process.closeWriteChannel();
    passwordBytes.fill('\0');

    const bool finished = process.waitForFinished(30000);
    if (!finished) {
        process.kill();
        process.waitForFinished(1000);
    }
    if (!finished || process.exitStatus() != QProcess::NormalExit || process.exitCode() != 0) {
        const QString helperError = QString::fromUtf8(process.readAllStandardError()).trimmed();
        setBusy(false);
        setAuthStatus(authError(helperError.isEmpty()
            ? QStringLiteral("KWallet is unavailable. Unlock KWallet, then try again.")
            : helperError));
        return;
    }

    setAuthStatus(callMap(QStringLiteral("BeginSignIn"), {trimmedAppleId, passwordSecretRef()}));
    setBusy(false);
}

void DaemonClient::beginSignIn(const QString &appleId, const QString &passwordSecretRef)
{
    setBusy(true);
    setAuthStatus(callMap(QStringLiteral("BeginSignIn"), {appleId.trimmed(), passwordSecretRef}));
    setBusy(false);
}

QString DaemonClient::passwordSecretRef() const
{
    return passwordSecretRefFor(QString::fromLatin1(DefaultAccountLabel));
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

void DaemonClient::setAuthStatus(const QVariantMap &status)
{
    m_authStatus = status.isEmpty()
        ? authError(QStringLiteral("iCloud Drive daemon is unavailable or did not return account status."))
        : status;
    Q_EMIT authStatusChanged();
}
