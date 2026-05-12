#include "daemonclient.h"

#include <KLocalizedString>

#include <QDir>
#include <QFileInfo>
#include <QProcess>
#include <QStandardPaths>
#include <QStringList>
#include <QTextStream>
#include <QVariantMap>

namespace
{
constexpr const char *ConfigMethod = "GetConfig";
constexpr const char *ItemStateMethod = "GetItemState";
constexpr const char *BalooIndexerConfigContract = "Baloo::IndexerConfig";

struct IndexingStatus {
    QString state;
    QString label;
    QString body;
    QString syncRoot;
    QStringList excludedPaths;
};

QString toolPath(const QString &name)
{
    return QStandardPaths::findExecutable(name);
}

bool hasRuntimeGate()
{
    return !toolPath(QStringLiteral("balooctl6")).isEmpty() && !toolPath(QStringLiteral("balooshow6")).isEmpty()
        && !toolPath(QStringLiteral("baloosearch6")).isEmpty();
}

QString balooStatusOutput()
{
    QProcess process;
    process.start(toolPath(QStringLiteral("balooctl6")), QStringList {QStringLiteral("status")});
    if (!process.waitForFinished(3000)) {
        process.kill();
        process.waitForFinished();
        return {};
    }
    return QString::fromLocal8Bit(process.readAllStandardOutput() + process.readAllStandardError());
}

QStringList sensitiveExclusions(const QVariantMap &config)
{
    QStringList exclusions {
        QStringLiteral("cache"),
        QStringLiteral("SQLite"),
        QStringLiteral("logs"),
        QStringLiteral("cookies"),
        QStringLiteral("tokens"),
        QStringLiteral("KWallet"),
    };

    const QString cacheDir = config.value(QStringLiteral("cache_dir")).toString();
    if (!cacheDir.isEmpty()) {
        exclusions.prepend(QDir::cleanPath(cacheDir));
    }
    return exclusions;
}
}

class BalooController
{
public:
    IndexingStatus status()
    {
        Q_UNUSED(ConfigMethod)
        Q_UNUSED(ItemStateMethod)
        Q_UNUSED(BalooIndexerConfigContract)

        m_client.refresh();
        const QVariantMap config = m_client.config();
        const QString syncRoot = config.value(QStringLiteral("sync_root")).toString();
        const QStringList exclusions = sensitiveExclusions(config);
        if (syncRoot.isEmpty()) {
            return {
                QStringLiteral("root_not_configured"),
                i18n("Waiting for setup"),
                i18n("Indexing status is unavailable. Check the sync folder in iCloud Drive settings."),
                QString(),
                exclusions,
            };
        }

        const QFileInfo rootInfo(syncRoot);
        if (!rootInfo.exists() || !rootInfo.isDir()) {
            return {
                QStringLiteral("error"),
                i18n("Indexing needs attention"),
                i18n("Indexing status is unavailable. Check the sync folder in iCloud Drive settings."),
                syncRoot,
                exclusions,
            };
        }

        if (!hasRuntimeGate()) {
            return {
                QStringLiteral("error"),
                i18n("Indexing needs attention"),
                i18n("Indexing status is unavailable. Check the sync folder in iCloud Drive settings."),
                rootInfo.canonicalFilePath(),
                exclusions,
            };
        }

        const QString balooStatus = balooStatusOutput();
        if (balooStatus.contains(QStringLiteral("disabled"), Qt::CaseInsensitive)) {
            return {
                QStringLiteral("disabled_by_user"),
                i18n("Indexing disabled"),
                i18n("KDE file indexing is disabled for this folder. You can still browse files in Dolphin."),
                rootInfo.canonicalFilePath(),
                exclusions,
            };
        }

        return {
            QStringLiteral("placeholders_name_only"),
            i18n("Placeholders name-only"),
            i18n("Remote-only placeholders are indexed by name only until they download."),
            rootInfo.canonicalFilePath(),
            exclusions,
        };
    }

    int printStatus()
    {
        const IndexingStatus current = status();
        QTextStream out(stdout);
        out << i18n("Search indexing") << '\n';
        out << current.state << '\n';
        out << current.label << '\n';
        out << current.body << '\n';
        if (!current.syncRoot.isEmpty()) {
            out << i18n("Hydrated files in your iCloud Drive folder can appear in KDE search.") << '\n';
            out << "hydrated_enabled" << '\n';
        }
        out << i18n("Excluded from indexing") << ": " << current.excludedPaths.join(QStringLiteral(", ")) << '\n';
        return current.state == QStringLiteral("error") ? 1 : 0;
    }

private:
    DaemonClient m_client;
};

int runBalooController()
{
    BalooController controller;
    return controller.printStatus();
}
