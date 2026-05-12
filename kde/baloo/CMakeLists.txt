find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED Core DBus)
find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS I18n)

add_executable(icloud-kde-baloo
    main.cpp
    baloocontroller.cpp
)

target_link_libraries(icloud-kde-baloo PRIVATE
    Qt::Core
    Qt::DBus
    KF6::I18n
    icloud-kde-common
)

install(TARGETS icloud-kde-baloo ${KDE_INSTALL_TARGETS_DEFAULT_ARGS})
