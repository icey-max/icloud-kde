import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "Recovery"

    required property var daemonClient

    ColumnLayout {
        width: page.width
        spacing: Kirigami.Units.largeSpacing

        Controls.Button {
            text: "Request re-authentication"
            icon.name: "view-refresh"
            onClicked: daemonClient.requestReauth()
        }

        Controls.Button {
            text: "Reveal local folder"
            icon.name: "folder-open"
            onClicked: daemonClient.revealSyncRoot()
        }

        Controls.Button {
            text: "Collect logs"
            icon.name: "document-save"
            onClicked: daemonClient.collectLogs("")
        }

        Controls.CheckBox {
            id: rebuildCacheAcknowledgement
            text: "Rebuild cache: Move the internal cache to a backup and rebuild it. Local files in the sync folder are not deleted."
            Layout.fillWidth: true
        }

        Controls.Button {
            text: "Rebuild cache"
            icon.name: "edit-delete"
            enabled: rebuildCacheAcknowledgement.checked
            onClicked: {
                if (rebuildCacheAcknowledgement.checked) {
                    daemonClient.rebuildCache("rebuild-cache")
                }
            }
        }

        Kirigami.InlineMessage {
            visible: true
            text: "iCloud web access or account security settings can block Linux access."
            type: Kirigami.MessageType.Information
            Layout.fillWidth: true
        }

        Controls.Label {
            text: "Advanced Data Protection may limit what this integration can read."
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Controls.Label {
            text: "Credentials and session material are stored in KWallet or a compatible secret-service backend, not plaintext project config."
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }
}
