import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "."

Rectangle {
    id: root
    anchors.fill: parent
    color: "#D9050811"
    z: 9999
    visible: opacity > 0
    opacity: 0

    signal cleared()

    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

    function open() {
        opacity = 1
        root.forceActiveFocus()
    }

    function close() {
        opacity = 0
    }

    // Dismiss on backdrop click
    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    Keys.onEscapePressed: root.close()

    Rectangle {
        id: card
        width: Math.min(parent.width - 40, 480)
        implicitHeight: cardCol.implicitHeight + 40
        anchors.centerIn: parent
        radius: Theme.radiusLg
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        clip: true

        scale: root.opacity > 0 ? 1.0 : 0.95
        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        ColumnLayout {
            id: cardCol
            anchors.fill: parent
            anchors.margins: 22
            spacing: 16

            // Header
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Rectangle {
                    width: 40
                    height: 40
                    radius: Theme.radiusMd
                    color: Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.15)
                    FaIcon {
                        anchors.centerIn: parent
                        icon: Icons.trash
                        size: 16
                        iconColor: Theme.danger
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: "Clear Download List"
                        color: Theme.textPrimary
                        font.pixelSize: 15
                        font.bold: true
                    }
                    Text {
                        text: "Select how you would like to clear downloaded models from disk"
                        color: Theme.textMuted
                        font.pixelSize: 11
                    }
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    width: 28
                    height: 28
                    radius: Theme.radiusSm
                    color: closeMouse.containsMouse ? Theme.surfaceElevated : "transparent"
                    FaIcon {
                        anchors.centerIn: parent
                        icon: Icons.times
                        size: 12
                        iconColor: Theme.textMuted
                    }
                    MouseArea {
                        id: closeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.border
            }

            // Description
            Text {
                text: "This action will remove downloaded articles and files from your local storage. Choose whether to remove only incomplete models or wipe the entire library."
                color: Theme.textSecondary
                font.pixelSize: 12
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            // Option 1: Clear Incomplete / Missing only
            Rectangle {
                Layout.fillWidth: true
                height: 52
                radius: Theme.radiusMd
                color: opt1Mouse.containsMouse ? Theme.surfaceElevated : Theme.card
                border.color: opt1Mouse.containsMouse ? Theme.warning : Theme.border
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    FaIcon {
                        icon: Icons.exclamationTriangle
                        size: 16
                        iconColor: Theme.warning
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: "Clear Incomplete / Missing Articles Only"
                            color: Theme.textPrimary
                            font.pixelSize: 12
                            font.bold: true
                        }
                        Text {
                            text: "Remove only folders that failed to download or lack a 3D model"
                            color: Theme.textMuted
                            font.pixelSize: 10
                        }
                    }

                    FaIcon {
                        icon: Icons.chevronRight
                        size: 10
                        iconColor: Theme.textMuted
                    }
                }

                MouseArea {
                    id: opt1Mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        Bridge.clearDownloadList("missing")
                        root.close()
                        root.cleared()
                    }
                }
            }

            // Option 2: Clear All Articles
            Rectangle {
                Layout.fillWidth: true
                height: 52
                radius: Theme.radiusMd
                color: opt2Mouse.containsMouse ? Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.15) : Theme.card
                border.color: opt2Mouse.containsMouse ? Theme.danger : Theme.border
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 12

                    FaIcon {
                        icon: Icons.trash
                        size: 16
                        iconColor: Theme.danger
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Text {
                            text: "Clear All Downloaded Articles"
                            color: Theme.danger
                            font.pixelSize: 12
                            font.bold: true
                        }
                        Text {
                            text: "Completely delete all locally stored models, images, and folders"
                            color: Theme.textMuted
                            font.pixelSize: 10
                        }
                    }

                    FaIcon {
                        icon: Icons.chevronRight
                        size: 10
                        iconColor: Theme.textMuted
                    }
                }

                MouseArea {
                    id: opt2Mouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        Bridge.clearDownloadList("all")
                        root.close()
                        root.cleared()
                    }
                }
            }

            // Footer Cancel
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }

                Rectangle {
                    width: 90
                    height: 34
                    radius: Theme.radiusSm
                    color: Theme.surfaceElevated
                    border.color: Theme.border

                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
                        color: Theme.textSecondary
                        font.pixelSize: 11
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }
        }
    }
}
