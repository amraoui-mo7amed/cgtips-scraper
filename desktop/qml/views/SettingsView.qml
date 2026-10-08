import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "../components"

Item {
    id: root

    Component.onCompleted: {
        Bridge.refreshStatus()
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: parent.width
        clip: true

        ColumnLayout {
            width: Math.min(parent.width - 40, 780)
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 24
            spacing: 20

            // Scraper Engine Status Card
            Rectangle {
                Layout.fillWidth: true
                height: engineCol.implicitHeight + 40
                radius: Theme.radiusLg
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                ColumnLayout {
                    id: engineCol
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    RowLayout {
                        spacing: 12
                        Rectangle {
                            width: 40
                            height: 40
                            radius: Theme.radiusMd
                            color: Qt.rgba(Theme.success.r, Theme.success.g, Theme.success.b, 0.15)
                            FaIcon {
                                anchors.centerIn: parent
                                icon: Icons.gear
                                size: 18
                                iconColor: Theme.success
                            }
                        }
                        ColumnLayout {
                            spacing: 2
                            Text {
                                text: "Direct Scraper Engine"
                                color: Theme.textPrimary
                                font.pixelSize: 15
                                font.bold: true
                            }
                            Text {
                                text: "Running directly in-process • No external REST API or server required"
                                color: Theme.success
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.border
                    }

                    // Feeds Storage Path
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Text {
                            text: "Storage Directory (Feeds)"
                            color: Theme.textSecondary
                            font.pixelSize: 12
                            font.bold: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.surfaceElevated
                                border.color: Theme.border

                                Text {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    text: Bridge.feedsDir
                                    color: Theme.primaryLight
                                    font.pixelSize: 12
                                    font.bold: true
                                    elide: Text.ElideMiddle
                                }
                            }

                            Rectangle {
                                width: 140
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.primary

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 6
                                    FaIcon {
                                        icon: Icons.folderOpen
                                        size: 12
                                        iconColor: "white"
                                    }
                                    Text {
                                        text: "Open in Finder"
                                        color: "white"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: Bridge.openFolder("")
                                }
                            }
                        }
                    }

                    // Scraper Browser Mode
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 24

                        ColumnLayout {
                            spacing: 4
                            Text { text: "BROWSER AUTOMATION"; color: Theme.textMuted; font.pixelSize: 9; font.bold: true }
                            Text { text: "Playwright Headless Chromium"; color: Theme.textPrimary; font.pixelSize: 12 }
                        }

                        ColumnLayout {
                            spacing: 4
                            Text { text: "LOCKER BYPASS"; color: Theme.textMuted; font.pixelSize: 9; font.bold: true }
                            Text { text: "Safelinku • Mega4up • GDrive"; color: Theme.textPrimary; font.pixelSize: 12 }
                        }
                    }
                }
            }

            // Storage Metrics Card
            Rectangle {
                Layout.fillWidth: true
                height: metricsCol.implicitHeight + 40
                radius: Theme.radiusLg
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                ColumnLayout {
                    id: metricsCol
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Text {
                        text: "Local Storage Metrics"
                        color: Theme.textPrimary
                        font.pixelSize: 15
                        font.bold: true
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 16

                        Rectangle {
                            Layout.fillWidth: true
                            height: 70
                            radius: Theme.radiusMd
                            color: Theme.surfaceElevated
                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 4
                                Text {
                                    text: Bridge.libraryTotal
                                    color: Theme.primaryLight
                                    font.pixelSize: 20
                                    font.bold: true
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    text: "3D Models Scraped"
                                    color: Theme.textMuted
                                    font.pixelSize: 10
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 70
                            radius: Theme.radiusMd
                            color: Theme.surfaceElevated
                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 4
                                Text {
                                    text: ((Bridge.statusData.library_summary && Bridge.statusData.library_summary.total_images) || 0)
                                    color: Theme.textPrimary
                                    font.pixelSize: 20
                                    font.bold: true
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    text: "Photos Cached"
                                    color: Theme.textMuted
                                    font.pixelSize: 10
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 70
                            radius: Theme.radiusMd
                            color: Theme.surfaceElevated
                            ColumnLayout {
                                anchors.centerIn: parent
                                spacing: 4
                                Text {
                                    text: ((Bridge.statusData.library_summary && Bridge.statusData.library_summary.total_size) || "0 B")
                                    color: Theme.success
                                    font.pixelSize: 20
                                    font.bold: true
                                    Layout.alignment: Qt.AlignHCenter
                                }
                                Text {
                                    text: "Disk Used"
                                    color: Theme.textMuted
                                    font.pixelSize: 10
                                    Layout.alignment: Qt.AlignHCenter
                                }
                            }
                        }
                    }
                }
            }

            // Client Agent & Multi-Destination Disks Card
            Rectangle {
                Layout.fillWidth: true
                height: clientCol.implicitHeight + 40
                radius: Theme.radiusLg
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                ColumnLayout {
                    id: clientCol
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    RowLayout {
                        spacing: 12
                        Rectangle {
                            width: 40
                            height: 40
                            radius: Theme.radiusMd
                            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.15)
                            FaIcon {
                                anchors.centerIn: parent
                                icon: Icons.desktop
                                size: 18
                                iconColor: Theme.primaryLight
                            }
                        }
                        ColumnLayout {
                            spacing: 2
                            Text {
                                text: "Client Agent & Multi-Destination Disks"
                                color: Theme.textPrimary
                                font.pixelSize: 15
                                font.bold: true
                            }
                            Text {
                                text: "Configure client agent executable and default target disks for simultaneous copying"
                                color: Theme.textMuted
                                font.pixelSize: 11
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.border
                    }

                    // Client Agent Executable Setting
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Text {
                            text: "Client Agent Executable (.exe)"
                            color: Theme.textSecondary
                            font.pixelSize: 12
                            font.bold: true
                        }

                        Text {
                            text: "This file will be automatically copied alongside 3D articles to every target destination disk."
                            color: Theme.textMuted
                            font.pixelSize: 11
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.surfaceElevated
                                border.color: Theme.border

                                Text {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    text: Bridge.clientAgentPath || "No client agent executable configured"
                                    color: Bridge.clientAgentPath ? Theme.primaryLight : Theme.textMuted
                                    font.pixelSize: 12
                                    font.bold: !!Bridge.clientAgentPath
                                    elide: Text.ElideMiddle
                                }
                            }

                            Rectangle {
                                width: 140
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.primary

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 6
                                    FaIcon {
                                        icon: Icons.folderOpen
                                        size: 11
                                        iconColor: "white"
                                    }
                                    Text {
                                        text: "Browse .exe..."
                                        color: "white"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: Bridge.selectClientAgentFile()
                                }
                            }

                            Rectangle {
                                visible: !!Bridge.clientAgentPath
                                width: 70
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.surfaceElevated
                                border.color: Theme.border

                                Text {
                                    anchors.centerIn: parent
                                    text: "Clear"
                                    color: Theme.danger
                                    font.pixelSize: 11
                                    font.bold: true
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: Bridge.clearClientAgentFile()
                                }
                            }
                        }
                    }

                    // Default Destination Disks
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Destination Disks / Folders (" + Bridge.copyDestinations.length + ")"
                                color: Theme.textSecondary
                                font.pixelSize: 12
                                font.bold: true
                            }
                            Item { Layout.fillWidth: true }

                            Rectangle {
                                width: 140
                                height: 30
                                radius: Theme.radiusSm
                                color: addDiskMouse2.containsMouse ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.25) : Theme.surfaceElevated
                                border.color: Theme.primary
                                border.width: 1

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 6
                                    FaIcon {
                                        icon: Icons.plus
                                        size: 10
                                        iconColor: Theme.primaryLight
                                    }
                                    Text {
                                        text: "Add Destination Disk"
                                        color: Theme.primaryLight
                                        font.pixelSize: 10
                                        font.bold: true
                                    }
                                }

                                MouseArea {
                                    id: addDiskMouse2
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: Bridge.addCopyDestination()
                                }
                            }

                            Rectangle {
                                visible: Bridge.copyDestinations.length > 0
                                width: 70
                                height: 30
                                radius: Theme.radiusSm
                                color: Theme.surfaceElevated
                                border.color: Theme.border

                                Text {
                                    anchors.centerIn: parent
                                    text: "Clear All"
                                    color: Theme.textMuted
                                    font.pixelSize: 10
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: Bridge.clearCopyDestinations()
                                }
                            }
                        }

                        // Disks List
                        Rectangle {
                            Layout.fillWidth: true
                            height: Math.min(Math.max(Bridge.copyDestinations.length * 36 + 12, 54), 160)
                            radius: Theme.radiusSm
                            color: Theme.surfaceElevated
                            border.color: Theme.border
                            clip: true

                            Text {
                                anchors.centerIn: parent
                                visible: Bridge.copyDestinations.length === 0
                                text: "No destination disks saved. Click '+ Add Destination Disk' to add USB drives or directories."
                                color: Theme.textMuted
                                font.pixelSize: 11
                            }

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 6
                                model: Bridge.copyDestinations
                                clip: true
                                spacing: 4

                                delegate: Rectangle {
                                    width: parent.width
                                    height: 32
                                    radius: 4
                                    color: Theme.card
                                    border.color: Theme.border

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        spacing: 8

                                        FaIcon {
                                            icon: Icons.hdd
                                            size: 11
                                            iconColor: Theme.primaryLight
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData
                                            color: Theme.textPrimary
                                            font.pixelSize: 11
                                            elide: Text.ElideMiddle
                                        }

                                        FaIcon {
                                            icon: Icons.times
                                            size: 11
                                            iconColor: Theme.danger
                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: Bridge.removeCopyDestination(modelData)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Google Drive API & Quota Bypass Card
            Rectangle {
                id: gdriveCard
                Layout.fillWidth: true
                height: gdriveCol.implicitHeight + 40
                radius: Theme.radiusLg
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                readonly property var status: Bridge.gdriveStatus || {}
                readonly property bool hasCreds: !!(status && status.credentials_present)
                readonly property bool hasToken: !!(status && status.authenticated)
                property string feedbackMessage: ""
                property bool feedbackSuccess: true
                property bool pasteMode: false
                property bool showHelp: false

                Connections {
                    target: Bridge
                    function onGdriveAuthFinished(success, message) {
                        gdriveCard.feedbackSuccess = success
                        gdriveCard.feedbackMessage = message
                    }
                    function onGdriveImportFinished(success, message) {
                        gdriveCard.feedbackSuccess = success
                        gdriveCard.feedbackMessage = message
                    }
                    function onGdriveTestFinished(success, message) {
                        gdriveCard.feedbackSuccess = success
                        gdriveCard.feedbackMessage = message
                    }
                }

                ColumnLayout {
                    id: gdriveCol
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    // Card Header
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Rectangle {
                            width: 40
                            height: 40
                            radius: Theme.radiusMd
                            color: gdriveCard.hasToken
                                ? Qt.rgba(Theme.success.r, Theme.success.g, Theme.success.b, 0.15)
                                : (gdriveCard.hasCreds
                                    ? Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.15)
                                    : Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.15))
                            FaIcon {
                                anchors.centerIn: parent
                                icon: Icons.cloudUpload
                                size: 18
                                iconColor: gdriveCard.hasToken
                                    ? Theme.success
                                    : (gdriveCard.hasCreds ? Theme.warning : Theme.primaryLight)
                            }
                        }

                        ColumnLayout {
                            spacing: 2
                            Layout.fillWidth: true
                            Text {
                                text: "Google Drive API & Quota Bypass"
                                color: Theme.textPrimary
                                font.pixelSize: 15
                                font.bold: true
                            }
                            Text {
                                text: "Import credentials.json to bypass Google Drive 'Quota exceeded' limits automatically"
                                color: Theme.textMuted
                                font.pixelSize: 11
                            }
                        }

                        // Status Badge
                        Rectangle {
                            radius: Theme.radiusSm
                            height: 28
                            Layout.preferredWidth: statusBadgeRow.implicitWidth + 16
                            color: gdriveCard.hasToken
                                ? Qt.rgba(Theme.success.r, Theme.success.g, Theme.success.b, 0.15)
                                : (gdriveCard.hasCreds
                                    ? Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.15)
                                    : Qt.rgba(Theme.textMuted.r, Theme.textMuted.g, Theme.textMuted.b, 0.15))
                            border.color: gdriveCard.hasToken
                                ? Theme.success
                                : (gdriveCard.hasCreds ? Theme.warning : Theme.border)

                            RowLayout {
                                id: statusBadgeRow
                                anchors.centerIn: parent
                                spacing: 6
                                FaIcon {
                                    icon: gdriveCard.hasToken
                                        ? Icons.checkCircle
                                        : (gdriveCard.hasCreds ? Icons.exclamationTriangle : Icons.infoCircle)
                                    size: 11
                                    iconColor: gdriveCard.hasToken
                                        ? Theme.success
                                        : (gdriveCard.hasCreds ? Theme.warning : Theme.textMuted)
                                }
                                Text {
                                    text: {
                                        if (gdriveCard.hasToken) {
                                            var email = (gdriveCard.status && gdriveCard.status.user_email) || ""
                                            return email ? "Connected • " + email : "Connected & Ready"
                                        }
                                        if (gdriveCard.hasCreds) return "Credentials Ready • Sign In Required"
                                        return "credentials.json Missing"
                                    }
                                    color: gdriveCard.hasToken
                                        ? Theme.success
                                        : (gdriveCard.hasCreds ? Theme.warning : Theme.textMuted)
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.border
                    }

                    // Credentials File Picker Section
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        Text {
                            text: "Google OAuth Credentials (credentials.json)"
                            color: Theme.textSecondary
                            font.pixelSize: 12
                            font.bold: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.surfaceElevated
                                border.color: Theme.border

                                Text {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    text: {
                                        if (gdriveCard.hasCreds) {
                                            var p = (gdriveCard.status && gdriveCard.status.credentials_path) || "credentials.json"
                                            var cid = (gdriveCard.status && gdriveCard.status.client_id) || ""
                                            if (cid && cid.length > 20) {
                                                return p + " (" + cid.substring(0, 16) + "...)"
                                            }
                                            return p
                                        }
                                        return "No credentials.json imported yet"
                                    }
                                    color: gdriveCard.hasCreds ? Theme.primaryLight : Theme.textMuted
                                    font.pixelSize: 12
                                    font.bold: gdriveCard.hasCreds
                                    elide: Text.ElideMiddle
                                }
                            }

                            // Import credentials.json button
                            Rectangle {
                                width: 180
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.primary

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 6
                                    FaIcon {
                                        icon: Icons.fileImport
                                        size: 12
                                        iconColor: "white"
                                    }
                                    Text {
                                        text: "Import credentials.json"
                                        color: "white"
                                        font.pixelSize: 11
                                        font.bold: true
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        gdriveCard.feedbackMessage = ""
                                        Bridge.chooseCredentialsFile()
                                    }
                                }
                            }

                            // Paste JSON toggle button
                            Rectangle {
                                width: 100
                                height: 38
                                radius: Theme.radiusSm
                                color: gdriveCard.pasteMode ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.25) : Theme.surfaceElevated
                                border.color: gdriveCard.pasteMode ? Theme.primary : Theme.border

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 6
                                    FaIcon {
                                        icon: Icons.copy
                                        size: 11
                                        iconColor: Theme.primaryLight
                                    }
                                    Text {
                                        text: gdriveCard.pasteMode ? "Hide Paste" : "Paste JSON"
                                        color: Theme.textPrimary
                                        font.pixelSize: 11
                                        font.bold: true
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: gdriveCard.pasteMode = !gdriveCard.pasteMode
                                }
                            }
                        }
                    }

                    // Paste JSON Text Area (collapsible)
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: gdriveCard.pasteMode
                        spacing: 8

                        Rectangle {
                            Layout.fillWidth: true
                            height: 120
                            radius: Theme.radiusSm
                            color: Theme.surfaceElevated
                            border.color: Theme.border

                            ScrollView {
                                anchors.fill: parent
                                anchors.margins: 8
                                TextArea {
                                    id: jsonTextInput
                                    placeholderText: "Paste contents of credentials.json here (must include 'installed' or 'web' client id)..."
                                    placeholderTextColor: Theme.textMuted
                                    color: Theme.textPrimary
                                    font.family: "Courier"
                                    font.pixelSize: 11
                                    wrapMode: Text.WrapAnywhere
                                    selectByMouse: true
                                }
                            }
                        }

                        RowLayout {
                            spacing: 8
                            ActionButton {
                                text: "Save Pasted Credentials"
                                icon: Icons.check
                                primary: true
                                enabled: jsonTextInput.text.trim().length > 0
                                onClicked: {
                                    Bridge.importCredentialsText(jsonTextInput.text)
                                    gdriveCard.pasteMode = false
                                }
                            }
                            ActionButton {
                                text: "Cancel"
                                icon: Icons.times
                                onClicked: gdriveCard.pasteMode = false
                            }
                        }
                    }

                    // Actions Row: Sign In, Test Connection, Disconnect
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        visible: gdriveCard.hasCreds

                        // Sign In with Google
                        Rectangle {
                            Layout.preferredWidth: 170
                            height: 38
                            radius: Theme.radiusSm
                            color: Bridge.isAuthenticatingGDrive ? Theme.surfaceElevated : Theme.primary
                            opacity: Bridge.isAuthenticatingGDrive ? 0.7 : 1.0

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 8
                                FaIcon {
                                    icon: Bridge.isAuthenticatingGDrive ? Icons.sync : Icons.cloudUpload
                                    size: 13
                                    iconColor: "white"
                                    RotationAnimator on rotation {
                                        running: Bridge.isAuthenticatingGDrive
                                        loops: Animation.Infinite
                                        from: 0
                                        to: 360
                                        duration: 1000
                                    }
                                }
                                Text {
                                    text: Bridge.isAuthenticatingGDrive
                                        ? "Waiting for Auth..."
                                        : (gdriveCard.hasToken ? "Re-authenticate" : "Sign In with Google")
                                    color: "white"
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                enabled: !Bridge.isAuthenticatingGDrive
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    gdriveCard.feedbackMessage = ""
                                    Bridge.authenticateGDrive()
                                }
                            }
                        }

                        // Test Connection
                        Rectangle {
                            Layout.preferredWidth: 140
                            height: 38
                            radius: Theme.radiusSm
                            color: Theme.surfaceElevated
                            border.color: Theme.border
                            opacity: !gdriveCard.hasToken || Bridge.isTestingGDrive ? 0.5 : 1.0

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                FaIcon {
                                    icon: Bridge.isTestingGDrive ? Icons.sync : Icons.bolt
                                    size: 12
                                    iconColor: Theme.primaryLight
                                    RotationAnimator on rotation {
                                        running: Bridge.isTestingGDrive
                                        loops: Animation.Infinite
                                        from: 0
                                        to: 360
                                        duration: 1000
                                    }
                                }
                                Text {
                                    text: Bridge.isTestingGDrive ? "Testing..." : "Test Drive API"
                                    color: Theme.textPrimary
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                enabled: gdriveCard.hasToken && !Bridge.isTestingGDrive
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    gdriveCard.feedbackMessage = ""
                                    Bridge.testGDriveConnection()
                                }
                            }
                        }

                        // Disconnect Token
                        Rectangle {
                            Layout.preferredWidth: 110
                            height: 38
                            radius: Theme.radiusSm
                            color: Theme.surfaceElevated
                            border.color: Theme.border
                            visible: gdriveCard.hasToken

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                FaIcon {
                                    icon: Icons.times
                                    size: 11
                                    iconColor: Theme.danger
                                }
                                Text {
                                    text: "Sign Out"
                                    color: Theme.danger
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.disconnectGDrive(false)
                            }
                        }

                        // Delete Credentials
                        Rectangle {
                            Layout.preferredWidth: 130
                            height: 38
                            radius: Theme.radiusSm
                            color: Theme.surfaceElevated
                            border.color: Theme.border

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                FaIcon {
                                    icon: Icons.trash
                                    size: 11
                                    iconColor: Theme.textMuted
                                }
                                Text {
                                    text: "Remove Creds"
                                    color: Theme.textMuted
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.disconnectGDrive(true)
                            }
                        }

                        Item { Layout.fillWidth: true }
                    }

                    // Prefer Drive API Toggle Checkbox
                    Rectangle {
                        Layout.fillWidth: true
                        height: 52
                        radius: Theme.radiusSm
                        color: Theme.surfaceElevated
                        border.color: Theme.border

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 12

                            CheckBox {
                                id: preferApiCheck
                                checked: Bridge.preferGDriveApi
                                onToggled: Bridge.setPreferGDriveApi(checked)
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Text {
                                    text: "Prefer Google Drive API for all downloads"
                                    color: Theme.textPrimary
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                                Text {
                                    text: "When unchecked (default), uses fast direct HTTP download first and uses Drive API only as an automatic quota bypass."
                                    color: Theme.textMuted
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }

                    // Feedback Message Banner
                    Rectangle {
                        Layout.fillWidth: true
                        height: 36
                        radius: Theme.radiusSm
                        visible: !!gdriveCard.feedbackMessage
                        color: gdriveCard.feedbackSuccess
                            ? Qt.rgba(Theme.success.r, Theme.success.g, Theme.success.b, 0.15)
                            : Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.15)
                        border.color: gdriveCard.feedbackSuccess ? Theme.success : Theme.danger

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 8
                            FaIcon {
                                icon: gdriveCard.feedbackSuccess ? Icons.checkCircle : Icons.timesCircle
                                size: 12
                                iconColor: gdriveCard.feedbackSuccess ? Theme.success : Theme.danger
                            }
                            Text {
                                text: gdriveCard.feedbackMessage
                                color: gdriveCard.feedbackSuccess ? Theme.success : Theme.danger
                                font.pixelSize: 11
                                font.bold: true
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            FaIcon {
                                icon: Icons.times
                                size: 10
                                iconColor: Theme.textMuted
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: gdriveCard.feedbackMessage = ""
                                }
                            }
                        }
                    }

                    // How to obtain credentials.json accordion
                    Rectangle {
                        Layout.fillWidth: true
                        radius: Theme.radiusSm
                        color: Theme.surfaceElevated
                        border.color: Theme.border
                        height: gdriveCard.showHelp ? helpCol.implicitHeight + 20 : 36
                        clip: true

                        Behavior on height { NumberAnimation { duration: 150 } }

                        ColumnLayout {
                            id: helpCol
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            Item {
                                Layout.fillWidth: true
                                height: 20

                                RowLayout {
                                    anchors.fill: parent
                                    spacing: 8
                                    FaIcon {
                                        icon: Icons.infoCircle
                                        size: 12
                                        iconColor: Theme.primaryLight
                                    }
                                    Text {
                                        text: "How to get credentials.json from Google Cloud Console"
                                        color: Theme.primaryLight
                                        font.pixelSize: 11
                                        font.bold: true
                                        Layout.fillWidth: true
                                    }
                                    FaIcon {
                                        icon: gdriveCard.showHelp ? Icons.chevronDown : Icons.chevronRight
                                        size: 10
                                        iconColor: Theme.textMuted
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: gdriveCard.showHelp = !gdriveCard.showHelp
                                }
                            }

                            Text {
                                visible: gdriveCard.showHelp
                                Layout.fillWidth: true
                                text: "1. Open Google Cloud Console (console.cloud.google.com) and create or select a project.\n" +
                                      "2. Navigate to 'APIs & Services' > 'Library', search for 'Google Drive API' and click 'Enable'.\n" +
                                      "3. Navigate to 'APIs & Services' > 'Credentials' > 'Create Credentials' > 'OAuth client ID'.\n" +
                                      "4. Select Application type: 'Desktop app' (name it 'CGTips 3D') and click 'Create'.\n" +
                                      "5. Click the Download JSON icon to get your credentials.json file.\n" +
                                      "6. Click 'Import credentials.json' above, then click 'Sign In with Google' to authorize."
                                color: Theme.textSecondary
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }

            // Loft Design Services API Configuration Card
            Rectangle {
                id: apiCard
                Layout.fillWidth: true
                height: apiCol.implicitHeight + 40
                radius: Theme.radiusLg
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                property bool isTestingApi: false
                property bool apiTestSuccess: false
                property string apiTestMessage: ""
                property bool passwordVisible: false

                Connections {
                    target: Bridge
                    function onApiConnectionTested(success, message) {
                        apiCard.isTestingApi = false
                        apiCard.apiTestSuccess = success
                        apiCard.apiTestMessage = message
                    }
                }

                ColumnLayout {
                    id: apiCol
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    // Card Header
                    RowLayout {
                        spacing: 12
                        Rectangle {
                            width: 40
                            height: 40
                            radius: Theme.radiusMd
                            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.15)
                            FaIcon {
                                anchors.centerIn: parent
                                icon: Icons.cloudUpload
                                size: 18
                                iconColor: Theme.primaryLight
                            }
                        }
                        ColumnLayout {
                            spacing: 2
                            Text {
                                text: "Loft Design API Configuration"
                                color: Theme.textPrimary
                                font.pixelSize: 15
                                font.bold: true
                            }
                            Text {
                                text: "Endpoint: https://loftdesign.bilnov.com/api/ • Admin credentials for article uploads"
                                color: Theme.textMuted
                                font.pixelSize: 11
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.border
                    }

                    // Username & Password Row
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        // Username / Email
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                text: "Username / Email"
                                color: Theme.textSecondary
                                font.pixelSize: 12
                                font.bold: true
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.surfaceElevated
                                border.color: apiUserField.activeFocus ? Theme.primary : Theme.border
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    spacing: 8

                                    FaIcon {
                                        icon: Icons.tag
                                        size: 11
                                        iconColor: Theme.textMuted
                                    }

                                    TextInput {
                                        id: apiUserField
                                        Layout.fillWidth: true
                                        text: Bridge.apiUsername
                                        color: Theme.textPrimary
                                        font.pixelSize: 12
                                        selectByMouse: true
                                        clip: true

                                        Text {
                                            text: "admin@loftdesign.com"
                                            color: Theme.textMuted
                                            font.pixelSize: 12
                                            visible: !apiUserField.text && !apiUserField.activeFocus
                                        }
                                    }
                                }
                            }
                        }

                        // Password Field
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                text: "Password"
                                color: Theme.textSecondary
                                font.pixelSize: 12
                                font.bold: true
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                height: 38
                                radius: Theme.radiusSm
                                color: Theme.surfaceElevated
                                border.color: apiPassField.activeFocus ? Theme.primary : Theme.border
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    spacing: 8

                                    FaIcon {
                                        icon: Icons.lock
                                        size: 11
                                        iconColor: Theme.textMuted
                                    }

                                    TextInput {
                                        id: apiPassField
                                        Layout.fillWidth: true
                                        text: Bridge.apiPassword
                                        echoMode: apiCard.passwordVisible ? TextInput.Normal : TextInput.Password
                                        color: Theme.textPrimary
                                        font.pixelSize: 12
                                        selectByMouse: true
                                        clip: true

                                        Text {
                                            text: "••••••••••••"
                                            color: Theme.textMuted
                                            font.pixelSize: 12
                                            visible: !apiPassField.text && !apiPassField.activeFocus
                                        }
                                    }

                                    FaIcon {
                                        icon: Icons.eye
                                        size: 11
                                        iconColor: apiCard.passwordVisible ? Theme.primaryLight : Theme.textMuted
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: apiCard.passwordVisible = !apiCard.passwordVisible
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Test Result Badge (if tested)
                    Rectangle {
                        Layout.fillWidth: true
                        height: 34
                        radius: Theme.radiusSm
                        visible: !!apiCard.apiTestMessage
                        color: apiCard.apiTestSuccess ? Qt.rgba(Theme.success.r, Theme.success.g, Theme.success.b, 0.15) : Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.15)
                        border.color: apiCard.apiTestSuccess ? Theme.success : Theme.danger
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            FaIcon {
                                icon: apiCard.apiTestSuccess ? Icons.checkCircle : Icons.timesCircle
                                size: 12
                                iconColor: apiCard.apiTestSuccess ? Theme.success : Theme.danger
                            }

                            Text {
                                Layout.fillWidth: true
                                text: apiCard.apiTestMessage
                                color: apiCard.apiTestSuccess ? Theme.success : Theme.danger
                                font.pixelSize: 11
                                font.bold: true
                                elide: Text.ElideRight
                            }
                        }
                    }

                    // Action Buttons Row
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        // Test Connection Button
                        Rectangle {
                            height: 38
                            Layout.fillWidth: true
                            radius: Theme.radiusSm
                            color: testConnMouse.containsMouse ? Theme.surfaceHover : Theme.surfaceElevated
                            border.color: Theme.border
                            border.width: 1

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 8
                                FaIcon {
                                    icon: apiCard.isTestingApi ? Icons.sync : Icons.bolt
                                    size: 11
                                    iconColor: Theme.primaryLight
                                }
                                Text {
                                    text: apiCard.isTestingApi ? "Testing Connection..." : "Test Connection"
                                    color: Theme.textPrimary
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                id: testConnMouse
                                anchors.fill: parent
                                enabled: !apiCard.isTestingApi
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    apiCard.isTestingApi = true
                                    apiCard.apiTestMessage = ""
                                    Bridge.testApiCredentials(
                                        apiUserField.text.trim(),
                                        apiPassField.text.trim()
                                    )
                                }
                            }
                        }

                        // Save Credentials Button
                        Rectangle {
                            height: 38
                            Layout.fillWidth: true
                            radius: Theme.radiusSm
                            color: saveCredsMouse.containsMouse ? Qt.darker(Theme.primary, 1.1) : Theme.primary

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 8
                                FaIcon {
                                    icon: Icons.check
                                    size: 11
                                    iconColor: "white"
                                }
                                Text {
                                    text: "Save Credentials"
                                    color: "white"
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                id: saveCredsMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    Bridge.setApiCredentials(
                                        apiUserField.text.trim(),
                                        apiPassField.text.trim()
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // Cache & Maintenance Card
            Rectangle {
                Layout.fillWidth: true
                height: maintCol.implicitHeight + 40
                radius: Theme.radiusLg
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                ColumnLayout {
                    id: maintCol
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 16

                    Text {
                        text: "Cache & Maintenance"
                        color: Theme.textPrimary
                        font.pixelSize: 15
                        font.bold: true
                    }

                    Text {
                        text: "Clear cached categories or session history to force the scraper to fetch fresh data from CGTips."
                        color: Theme.textMuted
                        font.pixelSize: 11
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Rectangle {
                            height: 38
                            Layout.fillWidth: true
                            radius: Theme.radiusSm
                            color: Theme.surfaceElevated
                            border.color: Theme.border

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                FaIcon {
                                    icon: Icons.trash
                                    size: 11
                                    iconColor: Theme.textSecondary
                                }
                                Text {
                                    text: "Clear Categories"
                                    color: Theme.textSecondary
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.clearCache("categories")
                            }
                        }

                        Rectangle {
                            height: 38
                            Layout.fillWidth: true
                            radius: Theme.radiusSm
                            color: Theme.surfaceElevated
                            border.color: Theme.border

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                FaIcon {
                                    icon: Icons.trash
                                    size: 11
                                    iconColor: Theme.textSecondary
                                }
                                Text {
                                    text: "Clear Feeds History"
                                    color: Theme.textSecondary
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.clearCache("history")
                            }
                        }

                        Rectangle {
                            height: 38
                            width: 120
                            radius: Theme.radiusSm
                            color: Theme.primary

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                FaIcon {
                                    icon: Icons.rotate
                                    size: 11
                                    iconColor: "white"
                                }
                                Text {
                                    text: "Rescan All"
                                    color: "white"
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    Bridge.loadLibrary()
                                    Bridge.loadCategories(true)
                                    Bridge.refreshStatus()
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
