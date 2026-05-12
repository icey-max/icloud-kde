import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: "Account"

    required property var daemonClient
    readonly property string authState: daemonClient.authStatus.state || "signed_out"
    readonly property string authMessage: daemonClient.authStatus.message || ""
    readonly property bool accountErrorVisible: authState === "error" || authState === "web_access_blocked" || authState === "account_blocked" || authState === "auth_required"
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
            text: authState === "trusted" ? "iCloud Drive" : "iCloud Drive is not connected"
            level: 2
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Controls.Label {
            text: authState === "error" ? "iCloud needs attention. Review the account message, then reconnect or update recovery settings." : "Connect your Apple ID to choose a local sync folder and start syncing."
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Controls.TextField {
            id: appleId
            placeholderText: "Apple ID"
            Layout.fillWidth: true
        }

        Controls.TextField {
            id: password
            placeholderText: "Apple ID password"
            echoMode: TextInput.Password
            inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
            Layout.fillWidth: true
        }

        Controls.Button {
            text: daemonClient.busy ? "Connecting..." : "Connect iCloud Drive"
            icon.name: "network-connect"
            enabled: !daemonClient.busy && appleId.text.trim().length > 0 && password.text.length > 0
            onClicked: {
                daemonClient.connectAccount(appleId.text, password.text)
                password.clear()
            }
        }

        Controls.Label {
            text: "Two-factor verification code"
            visible: authState === "needs_2fa"
            Layout.fillWidth: true
        }

        RowLayout {
            visible: authState === "needs_2fa"
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
            visible: authState === "needs_2sa_device" || authState === "needs_2sa_code"
            Layout.fillWidth: true
        }

        Controls.ComboBox {
            id: trustedDevice
            visible: authState === "needs_2sa_device" || authState === "needs_2sa_code"
            textRole: "label"
            valueRole: "device_id"
            model: daemonClient.authStatus.devices || []
            Layout.fillWidth: true
        }

        RowLayout {
            visible: authState === "needs_2sa_device" || authState === "needs_2sa_code"
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
            visible: accountErrorVisible
            text: authMessage
            type: Kirigami.MessageType.Error
            Layout.fillWidth: true
        }

        Controls.Button {
            text: "Reconnect"
            icon.name: "view-refresh"
            visible: authState === "auth_required"
            onClicked: daemonClient.requestReauth()
        }
    }
}
