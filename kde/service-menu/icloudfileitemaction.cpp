#include "daemonclient.h"
#include "pathguard.h"

#include <KAbstractFileItemActionPlugin>
#include <KFileItemListProperties>
#include <KLocalizedString>
#include <KPluginFactory>

#include <QAction>
#include <QDesktopServices>
#include <QIcon>
#include <QMap>
#include <QMessageBox>
#include <QPointer>
#include <QUrl>
#include <QVariantList>
#include <QVariantMap>
#include <QWidget>

namespace
{
constexpr const char *RevealSyncRootMethod = "RevealSyncRoot";
constexpr const char *GetItemStateMethod = "GetItemState";
constexpr const char *ListProblemItemsMethod = "ListProblemItems";
constexpr const char *PauseMethod = "Pause";
constexpr const char *ResumeMethod = "Resume";

QString itemState(const QVariantMap &state)
{
    return state.value(QStringLiteral("state")).toString();
}

QString labelForItemState(const QString &state)
{
    if (state == QLatin1String("placeholder")) {
        return i18n("Stored in iCloud");
    }
    if (state == QLatin1String("dirty")) {
        return i18n("Waiting to sync");
    }
    if (state == QLatin1String("syncing")) {
        return i18n("Syncing now");
    }
    if (state == QLatin1String("conflicted")) {
        return i18n("Conflict saved");
    }
    if (state == QLatin1String("offline")) {
        return i18n("Offline");
    }
    if (state == QLatin1String("auth_required")) {
        return i18n("Sign-in required");
    }
    if (state == QLatin1String("unsupported")) {
        return i18n("Unsupported item");
    }
    if (state == QLatin1String("error")) {
        return i18n("Status unavailable");
    }
    return i18n("Available offline");
}

QString detailForItemState(const QString &state)
{
    if (state == QLatin1String("placeholder")) {
        return i18n("The file downloads before its contents can be opened or indexed.");
    }
    if (state == QLatin1String("dirty")) {
        return i18n("Local changes are preserved and waiting to upload.");
    }
    if (state == QLatin1String("syncing")) {
        return i18n("The file is currently being updated.");
    }
    if (state == QLatin1String("conflicted")) {
        return i18n("A conflict copy requires review before deleting either version.");
    }
    if (state == QLatin1String("offline")) {
        return i18n("Changes will sync when the connection returns.");
    }
    if (state == QLatin1String("auth_required")) {
        return i18n("Reconnect iCloud Drive to resume syncing.");
    }
    if (state == QLatin1String("unsupported")) {
        return i18n("This file type is not supported by iCloud Drive sync.");
    }
    if (state == QLatin1String("error")) {
        return i18n("Open iCloud Drive settings to review the problem.");
    }
    return i18n("This file is stored locally.");
}

bool problemMatchesPath(const QVariantMap &problem, const QString &absolutePath)
{
    return problem.value(QStringLiteral("path")).toString() == absolutePath
        && problem.value(QStringLiteral("kind")).toString() == QLatin1String("conflict");
}

QString parentText(const PathGuard::Selection &selection)
{
    if (selection.paths.size() == 1) {
        return PathGuard::displayPath(selection.paths.first().relativePath);
    }
    return i18np("%1 selected item", "%1 selected items", selection.paths.size());
}
}

class ICloudFileItemAction : public KAbstractFileItemActionPlugin
{
    Q_OBJECT

public:
    explicit ICloudFileItemAction(QObject *parent = nullptr)
        : KAbstractFileItemActionPlugin(parent)
    {
    }

    QList<QAction *> actions(const KFileItemListProperties &fileItemInfos, QWidget *parentWidget) override
    {
        m_client.refresh();
        const QString syncRoot = m_client.config().value(QStringLiteral("sync_root")).toString();
        const PathGuard::Selection selection = PathGuard::validateSelection(fileItemInfos.urlList(), syncRoot);
        if (!selection.valid) {
            return {};
        }

        QList<QAction *> result;
        QPointer<QWidget> parent(parentWidget);

        auto *openRoot = new QAction(QIcon::fromTheme(QStringLiteral("document-open-folder")),
                                     i18n("Open iCloud Folder"),
                                     parentWidget);
        openRoot->setData(QString::fromLatin1(RevealSyncRootMethod));
        connect(openRoot, &QAction::triggered, this, [this, selection]() {
            m_client.revealSyncRoot();
            QDesktopServices::openUrl(QUrl::fromLocalFile(selection.syncRoot));
        });
        result.append(openRoot);

        auto *showStatus = new QAction(QIcon::fromTheme(QStringLiteral("view-list-details")),
                                       i18n("Show iCloud Drive Status"),
                                       parentWidget);
        showStatus->setData(QString::fromLatin1(GetItemStateMethod));
        connect(showStatus, &QAction::triggered, this, [this, selection, parent]() {
            showStatusDialog(selection, parent.data());
        });
        result.append(showStatus);

        const bool paused = m_client.serviceStatus().value(QStringLiteral("state")).toString() == QLatin1String("paused")
            || m_client.serviceStatus().value(QStringLiteral("paused")).toBool();
        auto *pauseResume = new QAction(QIcon::fromTheme(paused ? QStringLiteral("media-playback-start")
                                                               : QStringLiteral("media-playback-pause")),
                                        paused ? i18n("Resume iCloud Drive Sync")
                                               : i18n("Pause iCloud Drive Sync"),
                                        parentWidget);
        pauseResume->setData(QString::fromLatin1(paused ? ResumeMethod : PauseMethod));
        connect(pauseResume, &QAction::triggered, this, [this, paused]() {
            if (paused) {
                m_client.resume();
            } else {
                m_client.pause();
            }
        });
        result.append(pauseResume);

        if (hasConflict(selection)) {
            auto *conflictDetails = new QAction(QIcon::fromTheme(QStringLiteral("documentinfo")),
                                                i18n("Show Conflict Details"),
                                                parentWidget);
            conflictDetails->setData(QString::fromLatin1(ListProblemItemsMethod));
            connect(conflictDetails, &QAction::triggered, this, [selection, parent]() {
                QMessageBox::information(parent.data(),
                                         i18n("iCloud Drive status"),
                                         i18n("%1\nCompare the conflict copy before deleting either version.",
                                              parentText(selection)));
            });
            result.append(conflictDetails);
        }

        return result;
    }

private:
    bool hasConflict(const PathGuard::Selection &selection)
    {
        Q_UNUSED(ListProblemItemsMethod)

        const QVariantList problems = m_client.problemItems();
        for (const PathGuard::ValidatedPath &path : selection.paths) {
            const QVariantMap state = m_client.getItemState(path.absolutePath);
            if (itemState(state) == QLatin1String("conflicted")) {
                return true;
            }
            for (const QVariant &problem : problems) {
                if (problemMatchesPath(problem.toMap(), path.absolutePath)) {
                    return true;
                }
            }
        }
        return false;
    }

    void showStatusDialog(const PathGuard::Selection &selection, QWidget *parentWidget)
    {
        if (selection.paths.size() > 1) {
            QMap<QString, int> counts;
            for (const PathGuard::ValidatedPath &path : selection.paths) {
                const QString state = itemState(m_client.getItemState(path.absolutePath));
                counts[state.isEmpty() ? QStringLiteral("error") : state] += 1;
            }

            QStringList lines;
            for (auto it = counts.cbegin(); it != counts.cend(); ++it) {
                lines.append(i18n("%1: %2", labelForItemState(it.key()), it.value()));
            }
            QMessageBox::information(parentWidget, i18n("iCloud Drive status"), lines.join(QLatin1Char('\n')));
            return;
        }

        const PathGuard::ValidatedPath path = selection.paths.first();
        const QString state = itemState(m_client.getItemState(path.absolutePath));
        QMessageBox::information(parentWidget,
                                 i18n("iCloud Drive status"),
                                 i18n("%1\n%2\nPath: %3",
                                      labelForItemState(state),
                                      detailForItemState(state),
                                      PathGuard::displayPath(path.relativePath)));
    }

    DaemonClient m_client;
};

K_PLUGIN_CLASS_WITH_JSON(ICloudFileItemAction, "icloudfileitemaction.json")

#include "icloudfileitemaction.moc"
