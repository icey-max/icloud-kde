#include <KWallet>

#include <QCoreApplication>
#include <QTextStream>

namespace
{
constexpr const char *FolderName = "iCloud KDE";
constexpr const char *ServiceName = "org.kde.ICloudDrive";

QString argValue(const QStringList &args, const QString &name)
{
    const int index = args.indexOf(name);
    if (index < 0 || index + 1 >= args.size()) {
        return {};
    }
    return args.at(index + 1);
}

QString keyFor(const QString &account, const QString &kind)
{
    return QStringLiteral("%1:%2:%3").arg(QString::fromLatin1(ServiceName), account, kind);
}

KWallet::Wallet *openWallet()
{
    KWallet::Wallet *wallet = KWallet::Wallet::openWallet(KWallet::Wallet::NetworkWallet(), 0);
    if (!wallet) {
        return nullptr;
    }
    if (!wallet->hasFolder(QString::fromLatin1(FolderName))) {
        wallet->createFolder(QString::fromLatin1(FolderName));
    }
    wallet->setFolder(QString::fromLatin1(FolderName));
    return wallet;
}

int usage()
{
    QTextStream err(stderr);
    err << "Usage: icloud-kde-secret-tool <status|store|lookup|delete> --account <label> --kind <kind>\n";
    return 64;
}
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    const QStringList args = app.arguments();
    if (args.size() < 2) {
        return usage();
    }

    const QString command = args.at(1);
    KWallet::Wallet *wallet = openWallet();
    if (!wallet) {
        QTextStream(stderr) << "KWallet is unavailable\n";
        return 1;
    }

    if (command == QStringLiteral("status")) {
        return 0;
    }

    const QString account = argValue(args, QStringLiteral("--account"));
    const QString kind = argValue(args, QStringLiteral("--kind"));
    if (account.isEmpty() || kind.isEmpty()) {
        return usage();
    }

    const QString key = keyFor(account, kind);
    if (command == QStringLiteral("store")) {
        QTextStream in(stdin);
        const QString value = in.readAll();
        return wallet->writePassword(key, value) == 0 ? 0 : 1;
    }
    if (command == QStringLiteral("lookup")) {
        QString value;
        if (wallet->readPassword(key, value) != 0) {
            return 1;
        }
        QTextStream(stdout) << value;
        return 0;
    }
    if (command == QStringLiteral("delete")) {
        return wallet->removeEntry(key) == 0 ? 0 : 1;
    }

    return usage();
}
