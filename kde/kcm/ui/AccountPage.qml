import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "Account"

    required property var daemonClient
    readonly property var knownAuthStates: [
        "signed_out",
        "needs_password",
        "authenticating",
        "needs_2fa",
        "needs_2sa_device",
        "needs_2sa_code",
        "trusted",
        "auth_required",
        "web_access_blocked",
        "account_blocked",
        "error"
    ]

    ColumnLayout {
        width: page.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.Heading {
            text: daemonClient.authStatus.state === "trusted" ? "iCloud Drive" : "iCloud Drive is not connected"
            level: 2
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Controls.Label {
            text: daemonClient.authStatus.state === "error" ? "iCloud needs attention. Review the account message, then reconnect or update recovery settings." : "Connect your Apple ID to choose a local sync folder and start syncing."
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Controls.TextField {
            id: appleId
            placeholderText: "Apple ID"
            Layout.fillWidth: true
        }

        Controls.TextField {
            id: passwordSecretRef
            placeholderText: "org.kde.ICloudDrive:default:apple_id_password"
            Layout.fillWidth: true
        }

        Controls.Button {
            text: "Connect iCloud Drive"
            icon.name: "network-connect"
            enabled: appleId.text.length > 0 && passwordSecretRef.text.length > 0
            onClicked: daemonClient.beginSignIn(appleId.text, passwordSecretRef.text)
        }

        Controls.Label {
            text: "Two-factor verification code"
            visible: daemonClient.authStatus.state === "needs_2fa"
            Layout.fillWidth: true
        }

        RowLayout {
            visible: daemonClient.authStatus.state === "needs_2fa"
            Layout.fillWidth: true

            Controls.TextField {
                id: twoFactorCode
                inputMethodHints: Qt.ImhDigitsOnly
                Layout.fillWidth: true
            }

            Controls.Button {
                text: "Submit"
                onClicked: daemonClient.submitTwoFactorCode(twoFactorCode.text)
            }
        }

        Controls.Label {
            text: "Trusted device"
            visible: daemonClient.authStatus.state === "needs_2sa_device" || daemonClient.authStatus.state === "needs_2sa_code"
            Layout.fillWidth: true
        }

        Controls.ComboBox {
            id: trustedDevice
            visible: daemonClient.authStatus.state === "needs_2sa_device" || daemonClient.authStatus.state === "needs_2sa_code"
            textRole: "label"
            valueRole: "device_id"
            model: daemonClient.authStatus.devices || []
            Layout.fillWidth: true
        }

        RowLayout {
            visible: daemonClient.authStatus.state === "needs_2sa_device" || daemonClient.authStatus.state === "needs_2sa_code"
            Layout.fillWidth: true

            Controls.Button {
                text: "Send code"
                onClicked: daemonClient.sendTwoStepCode(trustedDevice.currentValue)
            }

            Controls.TextField {
                id: twoStepCode
                inputMethodHints: Qt.ImhDigitsOnly
                Layout.fillWidth: true
            }

            Controls.Button {
                text: "Submit"
                onClicked: daemonClient.submitTwoStepCode(trustedDevice.currentValue, twoStepCode.text)
            }
        }

        Kirigami.InlineMessage {
            visible: daemonClient.authStatus.state === "web_access_blocked" || daemonClient.authStatus.state === "account_blocked" || daemonClient.authStatus.state === "auth_required"
            text: daemonClient.authStatus.message || ""
            type: Kirigami.MessageType.Error
            Layout.fillWidth: true
        }

        Controls.Button {
            text: "Reconnect"
            icon.name: "view-refresh"
            visible: daemonClient.authStatus.state === "auth_required"
            onClicked: daemonClient.requestReauth()
        }
    }
}
