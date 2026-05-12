find_package(Qt6 ${QT_MIN_VERSION} CONFIG REQUIRED Core DBus)

add_library(icloud-kde-common STATIC
    daemonclient.cpp
    daemonclient.h
)

target_link_libraries(icloud-kde-common PUBLIC
    Qt::Core
    Qt::DBus
)

target_include_directories(icloud-kde-common PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)
