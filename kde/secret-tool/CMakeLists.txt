find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED Core)
find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS Wallet I18n)

add_executable(icloud-kde-secret-tool main.cpp)
target_link_libraries(icloud-kde-secret-tool PRIVATE Qt6::Core KF6::Wallet KF6::I18n)

install(TARGETS icloud-kde-secret-tool ${KDE_INSTALL_TARGETS_DEFAULT_ARGS})
