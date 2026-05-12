#include "daemonclient.h"

#include <KLocalizedString>
#include <KNotification>
#include <KStatusNotifierItem>

#include <QAction>
#include <QApplication>
#include <QDateTime>
#include <QFileInfo>
#include <QIcon>
#include <QMap>
#include <QMenu>
#include <QObject>
#include <QPointer>
#include <QProcess>
#include <QVariantList>
#include <QVariantMap>

#include <functional>

namespace
{
constexpr const char *MenuOrderContract =
    "iCloud Drive Open iCloud Folder Show Sync Status Sync Now Pause Sync Resume Sync "
    "Review Conflicts Reconnect iCloud Drive iCloud Drive Settings...";

constexpr const char *ComponentName = "icloud-kde";
constexpr const char *AuthRequiredEvent = "auth_required";
constexpr const char *AccountBlockedEvent = "account_blocked";
constexpr const char *ConflictCreatedEvent = "conflict_created";
constexpr const char *UploadStuckEvent = "upload_stuck";
constexpr const char *SyncPausedEvent = "sync_paused";
constexpr const char *SyncResumedEvent = "sync_resumed";
constexpr const char *HydrationCompletedEvent = "hydration_completed";

constexpr const char *RevealSyncRootMethod = "RevealSyncRoot";
constexpr const char *RequestSyncMethod = "RequestSync";
constexpr const char *PauseMethod = "Pause";
constexpr const char *ResumeMethod = "Resume";
constexpr const char *RequestReauthMethod = "RequestReauth";
constexpr const char *ListProblemItemsMethod = "ListProblemItems";

QString stateString(const QVariantMap &status)
{
    return status.value(QStringLiteral("state")).toString();
}

int problemCount(const QVariantList &problems)
{
    return problems.size();
}

bool hasKind(const QVariantList &problems, const QString &kind)
{
    for (const QVariant &item : problems) {
        if (item.toMap().value(QStringLiteral("kind")).toString() == kind) {
            return true;
        }
    }
    return false;
}

QString safeName(const QString &path)
{
    const QString name = QFileInfo(path).fileName();
    if (name.isEmpty() || name.contains(QLatin1Char('@'))) {
        return i18n("this item");
    }
    return name;
}

QString iconForState(const QString &state, const QVariantList &problems)
{
    if (state == QLatin1String("auth_required") || state == QLatin1String("account_blocked")
        || state == QLatin1String("web_access_blocked")) {
        return QStringLiteral("dialog-error");
    }
    if (state == QLatin1String("offline")) {
        return QStringLiteral("network-disconnect");
    }
    if (state == QLatin1String("paused")) {
        return QStringLiteral("media-playback-pause");
    }
    if (state == QLatin1String("syncing") || state == QLatin1String("scanning")
        || state == QLatin1String("starting")) {
        return QStringLiteral("folder-sync");
    }
    if (state == QLatin1String("degraded") || hasKind(problems, QStringLiteral("conflict"))
        || hasKind(problems, QStringLiteral("upload_stuck"))) {
        return QStringLiteral("messagebox_warning");
    }
    return QStringLiteral("folder-cloud");
}

QString labelForState(const QString &state)
{
    if (state == QLatin1String("starting")) {
        return i18n("Starting");
    }
    if (state == QLatin1String("scanning")) {
        return i18n("Scanning files");
    }
    if (state == QLatin1String("syncing")) {
        return i18n("Syncing");
    }
    if (state == QLatin1String("paused")) {
        return i18n("Paused");
    }
    if (state == QLatin1String("offline")) {
        return i18n("Offline");
    }
    if (state == QLatin1String("auth_required")) {
        return i18n("Sign-in required");
    }
    if (state == QLatin1String("account_blocked")) {
        return i18n("Account blocked");
    }
    if (state == QLatin1String("web_access_blocked")) {
        return i18n("Web access blocked");
    }
    if (state == QLatin1String("degraded")) {
        return i18n("Needs attention");
    }
    if (state == QLatin1String("stopping")) {
        return i18n("Stopping");
    }
    return i18n("Up to date");
}

QString progressTooltip(const QVariantMap &status, const QString &label)
{
    const QVariantMap progress = status.value(QStringLiteral("progress")).toMap();
    const int total = progress.value(QStringLiteral("total")).toInt();
    const int completed = progress.value(QStringLiteral("completed")).toInt();
    if (stateString(status) == QLatin1String("syncing") && total > 0) {
        return i18n("iCloud Drive - Syncing %1/%2", completed, total);
    }
    if (label == QLatin1String("Up to date")) {
        return i18n("iCloud Drive - Up to date");
    }
    return i18n("iCloud Drive - %1", label);
}
}

class NotificationPolicy : public QObject
{
    Q_OBJECT

public:
    explicit NotificationPolicy(QApplication &app)
        : QObject(&app)
        , m_client(new DaemonClient(this))
        , m_item(new KStatusNotifierItem(QStringLiteral("org.kde.ICloudDrive"), this))
        , m_menu(new QMenu)
    {
        Q_UNUSED(MenuOrderContract)
        m_item->setCategory(KStatusNotifierItem::SystemServices);
        m_item->setStatus(KStatusNotifierItem::Active);
        m_item->setIconByName(QStringLiteral("folder-cloud"));
        m_item->setContextMenu(m_menu);

        connect(m_client, &DaemonClient::serviceStatusChanged, this, &NotificationPolicy::handleStatus);
        connect(m_client, &DaemonClient::authStatusChanged, this, &NotificationPolicy::handleAuthStatus);
        connect(m_client, &DaemonClient::configChanged, this, &NotificationPolicy::syncPlaces);
        connect(m_client, &DaemonClient::problemItemsChanged, this, &NotificationPolicy::handleProblems);
        connect(m_client, &DaemonClient::problemRaised, this, &NotificationPolicy::handleProblem);
        connect(m_client, &DaemonClient::itemStateChanged, this, &NotificationPolicy::handleItemState);
        connect(m_client, &DaemonClient::progressChanged, this, &NotificationPolicy::handleProgress);

        syncPlaces(m_client->config());
        rebuildStatus();
        m_client->startPolling(30000);
    }

private:
    void handleStatus(const QVariantMap &status)
    {
        const QString current = stateString(status);
        if (current == QLatin1String("paused") && m_lastState != QLatin1String("paused")) {
            sendSyncPaused();
        } else if (m_lastState == QLatin1String("paused") && current != QLatin1String("paused")) {
            sendSyncResumed();
        }

        updatePersistentStatusNotifications(current);
        m_lastState = current;
        rebuildStatus();
    }

    void handleAuthStatus(const QVariantMap &authStatus)
    {
        const QString state = authStatus.value(QStringLiteral("state")).toString();
        if (state == QLatin1String("auth_required")) {
            showPersistent(QString::fromLatin1(AuthRequiredEvent),
                           i18n("iCloud Drive needs sign-in"),
                           i18n("Reconnect to resume syncing your iCloud Drive files."),
                           KNotification::CriticalUrgency,
                           {{i18n("Reconnect iCloud Drive"), [this]() {
                                 m_client->requestReauth();
                                 openSettings();
                             }},
                            {i18n("Open Settings"), [this]() {
                                 openSettings();
                             }}});
            return;
        }
        closePersistent(QString::fromLatin1(AuthRequiredEvent));
    }

    void handleProblems(const QVariantList &problems)
    {
        for (const QVariant &item : problems) {
            handleProblem(item.toMap());
        }
        rebuildStatus();
    }

    void handleProblem(const QVariantMap &problem)
    {
        const QString kind = problem.value(QStringLiteral("kind")).toString();
        const QString path = problem.value(QStringLiteral("path")).toString();
        if (kind == QLatin1String("conflict")) {
            notifyConflict(path);
        } else if (kind == QLatin1String("upload_stuck")) {
            notifyUploadStuck(path);
        } else if (kind == QLatin1String("auth_required")) {
            handleStatus({{QStringLiteral("state"), QStringLiteral("auth_required")}});
        } else if (kind == QLatin1String("account_blocked") || kind == QLatin1String("web_access_blocked")) {
            handleStatus({{QStringLiteral("state"), QStringLiteral("account_blocked")}});
        }
    }

    void handleItemState(const QString &path, const QVariantMap &state)
    {
        if (state.value(QStringLiteral("state")).toString() == QLatin1String("hydrated")
            && state.value(QStringLiteral("foreground_hydration")).toBool()) {
            sendHydrationCompleted(path);
        }
    }

    void handleProgress(const QVariantMap &progress)
    {
        const QString path = progress.value(QStringLiteral("path")).toString();
        if (progress.value(QStringLiteral("foreground_hydration")).toBool()
            && progress.value(QStringLiteral("state")).toString() == QLatin1String("hydrated")) {
            sendHydrationCompleted(path);
        }
    }

    void updatePersistentStatusNotifications(const QString &state)
    {
        if (state == QLatin1String("auth_required")) {
            showPersistent(QString::fromLatin1(AuthRequiredEvent),
                           i18n("iCloud Drive needs sign-in"),
                           i18n("Reconnect to resume syncing your iCloud Drive files."),
                           KNotification::CriticalUrgency,
                           {{i18n("Reconnect iCloud Drive"), [this]() {
                                 m_client->requestReauth();
                                 openSettings();
                             }},
                            {i18n("Open Settings"), [this]() {
                                 openSettings();
                             }}});
        } else {
            closePersistent(QString::fromLatin1(AuthRequiredEvent));
        }

        if (state == QLatin1String("account_blocked") || state == QLatin1String("web_access_blocked")) {
            showPersistent(QString::fromLatin1(AccountBlockedEvent),
                           i18n("iCloud Drive access is blocked"),
                           i18n("Account security or iCloud web access settings are blocking Linux access."),
                           KNotification::CriticalUrgency,
                           {{i18n("Open Settings"), [this]() {
                                 openSettings();
                             }}});
        } else {
            closePersistent(QString::fromLatin1(AccountBlockedEvent));
        }
    }

    using NotificationAction = QPair<QString, std::function<void()>>;

    void showPersistent(const QString &eventId,
                        const QString &title,
                        const QString &body,
                        KNotification::Urgency urgency,
                        const QList<NotificationAction> &actions)
    {
        if (m_persistentNotifications.contains(eventId)) {
            return;
        }
        KNotification *notification = createNotification(eventId, title, body, urgency, KNotification::Persistent);
        for (const auto &entry : actions) {
            KNotificationAction *action = notification->addAction(entry.first);
            connect(action, &KNotificationAction::activated, this, entry.second);
        }
        connect(notification, &KNotification::closed, this, [this, eventId]() {
            m_persistentNotifications.remove(eventId);
        });
        m_persistentNotifications.insert(eventId, notification);
        notification->sendEvent();
    }

    void closePersistent(const QString &eventId)
    {
        QPointer<KNotification> notification = m_persistentNotifications.take(eventId);
        if (notification) {
            notification->close();
        }
    }

    KNotification *createNotification(const QString &eventId,
                                      const QString &title,
                                      const QString &body,
                                      KNotification::Urgency urgency,
                                      KNotification::NotificationFlags flags = KNotification::CloseOnTimeout)
    {
        auto *notification = new KNotification(eventId, flags, this);
        notification->setComponentName(QString::fromLatin1(ComponentName));
        notification->setIconName(QStringLiteral("folder-cloud"));
        notification->setTitle(title);
        notification->setText(body);
        notification->setUrgency(urgency);
        return notification;
    }

    void notifyConflict(const QString &path)
    {
        const QDateTime now = QDateTime::currentDateTimeUtc();
        m_conflictWindow.append(now);
        while (!m_conflictWindow.isEmpty() && m_conflictWindow.first().secsTo(now) > 5 * 60) {
            m_conflictWindow.removeFirst();
        }

        QString title = i18n("iCloud Drive conflict saved");
        QString body = i18n("A conflict copy was saved for %1. Review it before deleting either version.", safeName(path));
        if (m_conflictWindow.size() > 3) {
            title = i18n("Multiple iCloud Drive conflicts saved");
            body = i18n("Review saved conflict copies before removing either version.");
        }

        KNotification *notification =
            createNotification(QString::fromLatin1(ConflictCreatedEvent), title, body, KNotification::NormalUrgency);
        KNotificationAction *showConflict = notification->addAction(i18n("Show Conflict"));
        connect(showConflict, &KNotificationAction::activated, this, &NotificationPolicy::reviewConflicts);
        KNotificationAction *openFolder = notification->addAction(i18n("Open Folder"));
        connect(openFolder, &KNotificationAction::activated, this, &NotificationPolicy::openFolder);
        notification->sendEvent();
    }

    void notifyUploadStuck(const QString &path)
    {
        const QDateTime now = QDateTime::currentDateTimeUtc();
        const QDateTime last = m_lastStuckUploadNotification.value(path);
        if (last.isValid() && last.secsTo(now) < 30 * 60) {
            return;
        }
        m_lastStuckUploadNotification.insert(path, now);

        KNotification *notification = createNotification(QString::fromLatin1(UploadStuckEvent),
                                                         i18n("iCloud Drive upload is stuck"),
                                                         i18n("%1 has not uploaded after repeated attempts. Review sync status.", safeName(path)),
                                                         KNotification::NormalUrgency);
        KNotificationAction *status = notification->addAction(i18n("Show Status"));
        connect(status, &KNotificationAction::activated, this, &NotificationPolicy::openSettings);
        KNotificationAction *pause = notification->addAction(i18n("Pause Sync"));
        connect(pause, &KNotificationAction::activated, m_client, &DaemonClient::pause);
        notification->sendEvent();
    }

    void sendSyncPaused()
    {
        KNotification *notification = createNotification(QString::fromLatin1(SyncPausedEvent),
                                                         i18n("iCloud Drive sync paused"),
                                                         i18n("Local changes stay in the folder and will sync after resume."),
                                                         KNotification::LowUrgency);
        KNotificationAction *resume = notification->addAction(i18n("Resume Sync"));
        connect(resume, &KNotificationAction::activated, m_client, &DaemonClient::resume);
        notification->sendEvent();
    }

    void sendSyncResumed()
    {
        KNotification *notification = createNotification(QString::fromLatin1(SyncResumedEvent),
                                                         i18n("iCloud Drive sync resumed"),
                                                         i18n("New changes will sync in the background."),
                                                         KNotification::LowUrgency);
        KNotificationAction *open = notification->addAction(i18n("Open Folder"));
        connect(open, &KNotificationAction::activated, this, &NotificationPolicy::openFolder);
        notification->sendEvent();
    }

    void sendHydrationCompleted(const QString &path)
    {
        if (path.isEmpty()) {
            return;
        }
        KNotification *notification = createNotification(QString::fromLatin1(HydrationCompletedEvent),
                                                         i18n("iCloud Drive file is ready"),
                                                         i18n("%1 is available locally.", safeName(path)),
                                                         KNotification::LowUrgency);
        KNotificationAction *show = notification->addAction(i18n("Show in Folder"));
        connect(show, &KNotificationAction::activated, this, &NotificationPolicy::openFolder);
        notification->sendEvent();
    }

    void rebuildStatus()
    {
        const QVariantMap status = m_client->serviceStatus();
        const QVariantList problems = m_client->problemItems();
        const bool serviceAvailable = !status.isEmpty();
        const QString state = stateString(status);
        const QString icon = serviceAvailable ? iconForState(state, problems) : QStringLiteral("dialog-error");
        QString label = serviceAvailable ? labelForState(state) : i18n("Service unavailable");
        const int count = problemCount(problems);
        if (serviceAvailable && count > 0) {
            label = i18np("%1 problem needs attention", "%1 problems need attention", count);
        }
        const QString fullTooltip =
            serviceAvailable ? progressTooltip(status, label) : i18n("iCloud Drive - Service unavailable");

        m_item->setIconByName(icon);
        m_item->setToolTip(icon, i18n("iCloud Drive"), fullTooltip);
        rebuildMenu(status, problems, serviceAvailable, icon, label);
    }

    void rebuildMenu(const QVariantMap &status,
                     const QVariantList &problems,
                     bool serviceAvailable,
                     const QString &icon,
                     const QString &label)
    {
        m_menu->clear();

        QAction *header = m_menu->addAction(QIcon::fromTheme(QStringLiteral("folder-cloud")), i18n("iCloud Drive"));
        header->setEnabled(false);

        QAction *statusRow = m_menu->addAction(QIcon::fromTheme(icon), label);
        statusRow->setEnabled(false);

        const QString syncRoot = m_client->config().value(QStringLiteral("sync_root")).toString();
        QAction *open = m_menu->addAction(QIcon::fromTheme(QStringLiteral("document-open-folder")), i18n("Open iCloud Folder"));
        open->setData(QString::fromLatin1(RevealSyncRootMethod));
        open->setEnabled(!syncRoot.isEmpty());
        connect(open, &QAction::triggered, this, &NotificationPolicy::openFolder);

        QAction *showStatus = m_menu->addAction(QIcon::fromTheme(QStringLiteral("view-list-details")), i18n("Show Sync Status"));
        showStatus->setEnabled(serviceAvailable);
        connect(showStatus, &QAction::triggered, this, &NotificationPolicy::openSettings);

        QAction *syncNow = m_menu->addAction(QIcon::fromTheme(QStringLiteral("folder-sync")), i18n("Sync Now"));
        syncNow->setData(QString::fromLatin1(RequestSyncMethod));
        syncNow->setEnabled(serviceAvailable && stateString(status) != QLatin1String("paused")
                            && stateString(status) != QLatin1String("auth_required")
                            && stateString(status) != QLatin1String("account_blocked")
                            && stateString(status) != QLatin1String("web_access_blocked"));
        connect(syncNow, &QAction::triggered, m_client, &DaemonClient::requestSync);

        QAction *pause = m_menu->addAction(QIcon::fromTheme(QStringLiteral("media-playback-pause")), i18n("Pause Sync"));
        pause->setData(QString::fromLatin1(PauseMethod));
        pause->setEnabled(serviceAvailable && stateString(status) != QLatin1String("paused"));
        connect(pause, &QAction::triggered, m_client, &DaemonClient::pause);

        QAction *resume = m_menu->addAction(QIcon::fromTheme(QStringLiteral("media-playback-start")), i18n("Resume Sync"));
        resume->setData(QString::fromLatin1(ResumeMethod));
        resume->setEnabled(serviceAvailable && stateString(status) == QLatin1String("paused"));
        connect(resume, &QAction::triggered, m_client, &DaemonClient::resume);

        QAction *review = m_menu->addAction(QIcon::fromTheme(QStringLiteral("documentinfo")), i18n("Review Conflicts"));
        review->setData(QString::fromLatin1(ListProblemItemsMethod));
        review->setVisible(hasKind(problems, QStringLiteral("conflict")));
        connect(review, &QAction::triggered, this, &NotificationPolicy::reviewConflicts);

        QAction *reauth = m_menu->addAction(QIcon::fromTheme(QStringLiteral("view-refresh")), i18n("Reconnect iCloud Drive"));
        reauth->setData(QString::fromLatin1(RequestReauthMethod));
        reauth->setVisible(stateString(status) == QLatin1String("auth_required"));
        connect(reauth, &QAction::triggered, this, &NotificationPolicy::reconnect);

        QAction *settings = m_menu->addAction(QIcon::fromTheme(QStringLiteral("configure")), i18n("iCloud Drive Settings..."));
        connect(settings, &QAction::triggered, this, &NotificationPolicy::openSettings);
    }

    void openFolder()
    {
        m_client->revealSyncRoot();
    }

    void openSettings()
    {
        QProcess::startDetached(QStringLiteral("kcmshell6"), QStringList {QStringLiteral("kcm_icloud")});
    }

    void reviewConflicts()
    {
        m_client->refresh();
        openSettings();
    }

    void reconnect()
    {
        m_client->requestReauth();
        openSettings();
    }

    void syncPlaces(const QVariantMap &config)
    {
        const QString syncRoot = config.value(QStringLiteral("sync_root")).toString();
        if (syncRoot.isEmpty() || syncRoot == m_lastPlacesSyncRoot) {
            return;
        }
        m_lastPlacesSyncRoot = syncRoot;
        QProcess::startDetached(QStringLiteral("icloud-kde-places"), QStringList {QStringLiteral("--sync")});
    }

    DaemonClient *m_client;
    KStatusNotifierItem *m_item;
    QMenu *m_menu;
    QString m_lastState;
    QString m_lastPlacesSyncRoot;
    QList<QDateTime> m_conflictWindow;
    QMap<QString, QDateTime> m_lastStuckUploadNotification;
    QMap<QString, QPointer<KNotification>> m_persistentNotifications;
};

int runNotifier(QApplication &app)
{
    NotificationPolicy policy(app);
    return app.exec();
}

#include "notificationpolicy.moc"
