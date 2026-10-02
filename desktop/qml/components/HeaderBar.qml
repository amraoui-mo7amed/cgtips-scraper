import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "."

Rectangle {
    id: root
    height: 60
    implicitHeight: 60
    Layout.preferredHeight: 60
    Layout.minimumHeight: 60
    Layout.fillWidth: true
    Layout.fillHeight: false
    color: Theme.surface
    border.color: Theme.border
    border.width: 1

    property string title: "CGTips 3D"
    property string subtitle: "Discover 3D models"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 16

        ColumnLayout {
            spacing: 2
            Text {
                text: root.title
                color: Theme.textPrimary
                font.pixelSize: 16
                font.bold: true
            }
            Text {
                text: root.subtitle
                color: Theme.textMuted
                font.pixelSize: 11
            }
        }

        Item {
            Layout.fillWidth: true
        }


        // Download / import status (click for the full list)
        DownloadStatusWidget {
            Layout.preferredWidth: implicitWidth
        }

        // Open Local Storage Button
        Rectangle {
            width: 36
            height: 36
            radius: Theme.radiusMd
            color: storageMouse.containsMouse ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.2) : Theme.surfaceElevated
            border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.3)

            RowLayout {
                anchors.centerIn: parent
                spacing: 6
                FaIcon {
                    icon: Icons.folderOpen
                    size: 12
                    iconColor: Theme.primaryLight
                }
            }

            MouseArea {
                id: storageMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: Bridge.openFolder("")
            }
        }
    }
}
