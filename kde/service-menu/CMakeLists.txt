find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED Core Gui Widgets DBus)
find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS CoreAddons I18n KIO)

kcoreaddons_add_plugin(icloudfileitemaction
    SOURCES icloudfileitemaction.cpp
    INSTALL_NAMESPACE "kf6/kfileitemaction"
)

target_link_libraries(icloudfileitemaction PRIVATE
    Qt::Core
    Qt::Gui
    Qt::Widgets
    Qt::DBus
    KF6::CoreAddons
    KF6::I18n
    KF6::KIOWidgets
    icloud-kde-common
)
