#include <KLocalizedString>

#include <QCoreApplication>
#include <QStringList>
#include <QTextStream>

int runBalooController();

namespace
{
int usage()
{
    QTextStream err(stderr);
    err << "Usage: icloud-kde-baloo --status\n";
    return 64;
}
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    KLocalizedString::setApplicationDomain("icloud-kde");

    const QStringList args = app.arguments();
    if (args.size() == 1 || (args.size() == 2 && args.at(1) == QStringLiteral("--status"))) {
        return runBalooController();
    }
    return usage();
}
