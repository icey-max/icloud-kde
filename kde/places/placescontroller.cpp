#include "placescontroller.h"

#include "daemonclient.h"

#include <KBookmark>
#include <KFilePlacesModel>
#include <KLocalizedString>

#include <QDir>
#include <QFileInfo>
#include <QModelIndex>
#include <QUrl>
#include <QVariantMap>

namespace
{
constexpr const char *ConfigMethod = "GetConfig";
constexpr const char *SyncRootKey = "sync_root";
constexpr const char *PlacesLabel = "iCloud Drive";
constexpr const char *PlacesIcon = "folder-cloud";

QModelIndex findPlaceByUrl(KFilePlacesModel &model, const QUrl &url)
{
    const KBookmark existing = model.bookmarkForUrl(url);
    if (existing.isNull()) {
        return {};
    }

    for (int row = 0; row < model.rowCount(); ++row) {
        const QModelIndex index = model.index(row, 0);
        if (model.bookmarkForIndex(index).url() == url) {
            return index;
        }
    }
    return {};
}

bool isProjectPlace(const KBookmark &bookmark)
{
    return !bookmark.isNull() && bookmark.fullText() == QString::fromLatin1(PlacesLabel)
        && bookmark.icon() == QString::fromLatin1(PlacesIcon) && bookmark.url().isLocalFile();
}
}

bool PlacesController::syncFromDaemon()
{
    Q_UNUSED(ConfigMethod)

    DaemonClient client;
    client.refresh();
    const QVariantMap config = client.config();
    const QString syncRoot = config.value(QString::fromLatin1(SyncRootKey)).toString();
    if (syncRoot.isEmpty()) {
        return removeProjectPlace();
    }

    const QFileInfo rootInfo(syncRoot);
    if (!rootInfo.exists() || !rootInfo.isDir()) {
        return false;
    }

    const QString canonicalRoot = rootInfo.canonicalFilePath();
    if (canonicalRoot.isEmpty()) {
        return false;
    }

    KFilePlacesModel model;
    const QUrl rootUrl = QUrl::fromLocalFile(canonicalRoot);
    const QModelIndex existingIndex = findPlaceByUrl(model, rootUrl);
    if (existingIndex.isValid()) {
        model.editPlace(existingIndex,
                        i18n("iCloud Drive"),
                        rootUrl,
                        QStringLiteral("folder-cloud"),
                        QString());
    } else {
        model.addPlace(i18n("iCloud Drive"), rootUrl, QStringLiteral("folder-cloud"), QString());
    }

    return true;
}

bool PlacesController::removeProjectPlace()
{
    KFilePlacesModel model;
    bool removed = false;
    for (int row = model.rowCount() - 1; row >= 0; --row) {
        const QModelIndex index = model.index(row, 0);
        if (isProjectPlace(model.bookmarkForIndex(index))) {
            model.removePlace(index);
            removed = true;
        }
    }
    return removed;
}
