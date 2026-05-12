#include "placescontroller.h"

#include <KLocalizedString>

#include <QApplication>
#include <QStringList>
#include <QTextStream>

namespace
{
int usage()
{
    QTextStream err(stderr);
    err << "Usage: icloud-kde-places --sync | --remove\n";
    return 64;
}
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    KLocalizedString::setApplicationDomain("icloud-kde");

    const QStringList args = app.arguments();
    if (args.size() != 2) {
        return usage();
    }

    PlacesController controller;
    const QString command = args.at(1);
    if (command == QStringLiteral("--sync")) {
        return controller.syncFromDaemon() ? 0 : 1;
    }
    if (command == QStringLiteral("--remove")) {
        controller.removeProjectPlace();
        return 0;
    }

    return usage();
}
