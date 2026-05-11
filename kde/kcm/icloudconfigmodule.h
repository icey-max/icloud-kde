#pragma once

#include <KQuickConfigModule>

class ICloudConfigModule : public KQuickConfigModule
{
    Q_OBJECT

public:
    ICloudConfigModule(QObject *parent, const KPluginMetaData &data);
};
