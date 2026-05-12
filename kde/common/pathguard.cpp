#include "pathguard.h"

#include <QDir>
#include <QFileInfo>
#include <QStringList>

namespace
{
bool isInsideRoot(const QString &canonicalPath, const QString &canonicalRoot)
{
    return canonicalPath == canonicalRoot || canonicalPath.startsWith(canonicalRoot + QDir::separator());
}

PathGuard::Selection invalidSelection(const QString &reason)
{
    PathGuard::Selection selection;
    selection.error = reason;
    return selection;
}
}

PathGuard::Selection PathGuard::validateSelection(const QList<QUrl> &urls, const QString &syncRoot)
{
    if (urls.isEmpty()) {
        return invalidSelection(QStringLiteral("empty selection"));
    }
    if (syncRoot.trimmed().isEmpty()) {
        return invalidSelection(QStringLiteral("missing sync_root"));
    }

    const QFileInfo rootInfo(syncRoot);
    const QString canonicalRoot = rootInfo.canonicalFilePath();
    if (canonicalRoot.isEmpty() || !rootInfo.isDir()) {
        return invalidSelection(QStringLiteral("invalid sync_root"));
    }

    Selection selection;
    selection.syncRoot = canonicalRoot;
    const QDir rootDir(canonicalRoot);

    for (const QUrl &url : urls) {
        if (!url.isLocalFile()) {
            return invalidSelection(QStringLiteral("non-local file URL"));
        }

        const QFileInfo itemInfo(url.toLocalFile());
        const QString canonicalPath = itemInfo.canonicalFilePath();
        if (canonicalPath.isEmpty() || !isInsideRoot(canonicalPath, canonicalRoot)) {
            return invalidSelection(QStringLiteral("selection outside sync_root"));
        }

        const QString relativePath = rootDir.relativeFilePath(canonicalPath);
        if (relativePath == QStringLiteral("..") || relativePath.startsWith(QStringLiteral("../"))) {
            return invalidSelection(QStringLiteral("relative path escaped sync_root"));
        }

        selection.paths.append({canonicalPath, relativePath});
    }

    selection.valid = true;
    return selection;
}

QString PathGuard::displayPath(const QString &relativePath)
{
    if (relativePath.isEmpty() || relativePath == QStringLiteral(".")) {
        return QStringLiteral(".");
    }

    const QStringList parts = relativePath.split(QDir::separator(), Qt::SkipEmptyParts);
    if (parts.size() <= 3) {
        return relativePath;
    }
    return parts.first() + QStringLiteral("/.../") + parts.last();
}
