#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class DaemonClient : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantMap authStatus READ authStatus NOTIFY authStatusChanged)
    Q_PROPERTY(QVariantMap serviceStatus READ serviceStatus NOTIFY serviceStatusChanged)
    Q_PROPERTY(QVariantMap config READ config NOTIFY configChanged)
    Q_PROPERTY(QVariantList problemItems READ problemItems NOTIFY problemItemsChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)

public:
    explicit DaemonClient(QObject *parent = nullptr);

    QVariantMap authStatus() const;
    QVariantMap serviceStatus() const;
    QVariantMap config() const;
    QVariantList problemItems() const;
    bool busy() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void beginSignIn(const QString &appleId, const QString &passwordSecretRef);
    Q_INVOKABLE void submitTwoFactorCode(const QString &code);
    Q_INVOKABLE QVariantList listTrustedDevices();
    Q_INVOKABLE void sendTwoStepCode(const QString &deviceId);
    Q_INVOKABLE void submitTwoStepCode(const QString &deviceId, const QString &code);
    Q_INVOKABLE void setSyncRoot(const QString &path);
    Q_INVOKABLE void requestReauth();
    Q_INVOKABLE void collectLogs(const QString &destination);
    Q_INVOKABLE void rebuildCache(const QString &confirmToken);
    Q_INVOKABLE void revealSyncRoot();

Q_SIGNALS:
    void authStatusChanged();
    void serviceStatusChanged();
    void configChanged();
    void problemItemsChanged();
    void busyChanged();

private:
    QVariantMap callMap(const QString &method, const QVariantList &args = {});
    QVariantList callList(const QString &method, const QVariantList &args = {});
    void setBusy(bool busy);

    QVariantMap m_authStatus;
    QVariantMap m_serviceStatus;
    QVariantMap m_config;
    QVariantList m_problemItems;
    bool m_busy = false;
};
