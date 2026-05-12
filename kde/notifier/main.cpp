#include <KLocalizedString>

#include <QApplication>

int runNotifier(QApplication &app);

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    KLocalizedString::setApplicationDomain("icloud-kde");
    QCoreApplication::setApplicationName(QStringLiteral("iCloud Drive"));
    QCoreApplication::setOrganizationName(QStringLiteral("KDE"));
    QApplication::setDesktopFileName(QStringLiteral("org.kde.icloud-drive.notifier"));

    return runNotifier(app);
}
