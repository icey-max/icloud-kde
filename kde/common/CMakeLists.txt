find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED Core DBus)

add_library(icloud-kde-common STATIC
    daemonclient.cpp
    daemonclient.h
    pathguard.cpp
    pathguard.h
)
set_target_properties(icloud-kde-common PROPERTIES POSITION_INDEPENDENT_CODE ON)

target_link_libraries(icloud-kde-common PUBLIC
    Qt::Core
    Qt::DBus
)

target_include_directories(icloud-kde-common PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)
