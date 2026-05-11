#include "icloudconfigmodule.h"
#include "daemonclient.h"

#include <KPluginFactory>

#include <QQmlEngine>

K_PLUGIN_CLASS_WITH_JSON(ICloudConfigModule, "kcm_icloud.json")

ICloudConfigModule::ICloudConfigModule(QObject *parent, const KPluginMetaData &data)
    : KQuickConfigModule(parent, data)
{
    qmlRegisterType<DaemonClient>("org.kde.icloudkde", 1, 0, "DaemonClient");
    setButtons(Help | Apply | Default);
}

#include "icloudconfigmodule.moc"
