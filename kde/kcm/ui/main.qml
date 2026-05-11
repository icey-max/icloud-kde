import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kcmutils as KCM
import org.kde.icloudkde 1.0

KCM.SimpleKCM {
    id: root

    DaemonClient {
        id: daemon
    }

    ColumnLayout {
        anchors.fill: parent

        Controls.TabBar {
            id: pageTabs
            Layout.fillWidth: true

            Controls.TabButton {
                text: "Account"
            }

            Controls.TabButton {
                text: "Sync"
            }

            Controls.TabButton {
                text: "Recovery"
            }
        }

        StackLayout {
            currentIndex: pageTabs.currentIndex
            Layout.fillWidth: true
            Layout.fillHeight: true

            AccountPage {
                daemonClient: daemon
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            SyncPage {
                daemonClient: daemon
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            RecoveryPage {
                daemonClient: daemon
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
}
