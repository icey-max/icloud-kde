import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "Sync"

    required property var daemonClient

    ColumnLayout {
        width: page.width
        spacing: Kirigami.Units.largeSpacing

        Controls.Label {
            text: "Sync root"
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true

            Controls.TextField {
                id: syncRoot
                text: daemonClient.config.sync_root || ""
                Layout.fillWidth: true
            }

            Controls.Button {
                icon.name: "folder-open"
                text: "Apply"
                onClicked: daemonClient.setSyncRoot(syncRoot.text)
            }
        }

        Controls.Label {
            text: "Cache location"
            Layout.fillWidth: true
        }

        Controls.TextField {
            id: cacheLocation
            text: daemonClient.config.cache_dir || ""
            Layout.fillWidth: true
        }

        Controls.Switch {
            id: startupBehavior
            text: "Start sync at login"
            checked: true
        }

        Controls.ComboBox {
            id: warmupMode
            model: ["background", "lazy"]
            currentIndex: 0
            Layout.fillWidth: true
        }

        Controls.SpinBox {
            id: concurrency
            from: 1
            to: 3
            value: 1
            editable: true
            Layout.fillWidth: true
        }

        Controls.Switch {
            id: pauseOnStartup
            text: "Pause on startup"
        }
    }
}
