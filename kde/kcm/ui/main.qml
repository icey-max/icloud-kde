import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM
import org.kde.icloudkde 1.0

KCM.SimpleKCM {
    id: root

    DaemonClient {
        id: daemonClient
    }

    Kirigami.PageRow {
        anchors.fill: parent
        globalToolBar.style: Kirigami.ApplicationHeaderStyle.None

        initialPage: AccountPage {
            daemonClient: daemonClient
        }

        Component.onCompleted: {
            push(syncPage)
            push(recoveryPage)
        }

        Component {
            id: syncPage
            SyncPage {
                daemonClient: daemonClient
            }
        }

        Component {
            id: recoveryPage
            RecoveryPage {
                daemonClient: daemonClient
            }
        }
    }
}
