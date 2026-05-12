find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED Core Widgets DBus)
find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS I18n Notifications StatusNotifierItem)

add_executable(icloud-kde-notifier
    main.cpp
    notificationpolicy.cpp
)

target_link_libraries(icloud-kde-notifier PRIVATE
    Qt::Core
    Qt::Widgets
    Qt::DBus
    KF6::I18n
    KF6::Notifications
    KF6::StatusNotifierItem
    icloud-kde-common
)

install(TARGETS icloud-kde-notifier ${KDE_INSTALL_TARGETS_DEFAULT_ARGS})
install(FILES icloud-kde.notifyrc DESTINATION ${KDE_INSTALL_KNOTIFYRCDIR})
install(FILES org.kde.icloud-drive.notifier.desktop DESTINATION ${KDE_INSTALL_APPDIR})
