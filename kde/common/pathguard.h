#pragma once

#include <QList>
#include <QString>
#include <QUrl>

class PathGuard
{
public:
    struct ValidatedPath {
        QString absolutePath;
        QString relativePath;
    };

    struct Selection {
        bool valid = false;
        QString syncRoot;
        QList<ValidatedPath> paths;
        QString error;
    };

    static Selection validateSelection(const QList<QUrl> &urls, const QString &syncRoot);
    static QString displayPath(const QString &relativePath);
};
