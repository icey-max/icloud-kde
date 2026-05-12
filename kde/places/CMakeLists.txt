find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED Core Widgets DBus)
find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS I18n KIO)

add_executable(icloud-kde-places
    main.cpp
    placescontroller.cpp
    placescontroller.h
)

target_link_libraries(icloud-kde-places PRIVATE
    Qt::Core
    Qt::Widgets
    Qt::DBus
    KF6::I18n
    KF6::KIOFileWidgets
    icloud-kde-common
)

install(TARGETS icloud-kde-places ${KDE_INSTALL_TARGETS_DEFAULT_ARGS})
