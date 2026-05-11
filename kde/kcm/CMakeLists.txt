find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED Core Quick Qml DBus)
find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS KCMUtils I18n CoreAddons Kirigami)

kcmutils_add_qml_kcm(kcm_icloud)
target_sources(kcm_icloud PRIVATE
    icloudconfigmodule.cpp
    icloudconfigmodule.h
    daemonclient.cpp
    daemonclient.h
)
target_link_libraries(kcm_icloud PRIVATE
    Qt::Core
    Qt::Quick
    Qt::Qml
    Qt::DBus
    KF6::KCMUtils
    KF6::I18n
    KF6::CoreAddons
)
