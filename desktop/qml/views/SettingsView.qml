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
