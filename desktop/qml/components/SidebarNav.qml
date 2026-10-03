import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "."

Rectangle {
    id: root
    width: 220
    implicitWidth: 220
    Layout.preferredWidth: 220
    Layout.minimumWidth: 220
    Layout.maximumWidth: 220
    Layout.fillWidth: false
    Layout.fillHeight: true
    color: Theme.surface
    border.color: Theme.border
    border.width: 1

    property int activeTab: 0 // 0: Categories, 1: Resolver, 2: Queue, 3: Library, 4: Settings
    signal tabSelected(int index)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        // Logo & Title
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Rectangle {
                width: 38
                height: 38
                radius: Theme.radiusMd
                color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.15)
                border.color: Qt.rgba(Theme.primaryLight.r, Theme.primaryLight.g, Theme.primaryLight.b, 0.3)

                FaIcon {
                    anchors.centerIn: parent
                    icon: Icons.cubes
                    size: 16
                    iconColor: Theme.primaryLight
                }
            }

            ColumnLayout {
                spacing: 2
                Text {
                    text: "CGTips Desktop"
                    color: Theme.textPrimary
                    font.pixelSize: 14
                    font.bold: true
                }
                Text {
                    text: "SketchUp 3D Platform"
                    color: Theme.textMuted
                    font.pixelSize: 10
                }
            }
        }

        // Divider
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.border
        }

        // Navigation Items
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6

            Repeater {
                model: [
                    { name: "Categories & Feeds", icon: Icons.layerGroup, index: 0 },
                    { name: "Direct Resolver", icon: Icons.bolt, index: 1 },
                    { name: "Download Queue", icon: Icons.listOl, index: 2 },
                    { name: "Downloads Library", icon: Icons.cubes, index: 3 },
                    { name: "Settings & Status", icon: Icons.gear, index: 4 }
                ]

                delegate: Rectangle {
                    id: navItem
                    Layout.fillWidth: true
                    height: 40
                    radius: Theme.radiusMd
                    color: {
                        if (root.activeTab === modelData.index) {
                            return Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.2);
                        }
                        return navMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.05) : "transparent";
                    }
                    border.color: root.activeTab === modelData.index ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.4) : "transparent"
                    border.width: 1

                    Behavior on color { ColorAnimation { duration: 150 } }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 12

                        FaIcon {
                            icon: modelData.icon
                            size: 14
                            iconColor: root.activeTab === modelData.index ? Theme.primaryLight : (navMouse.containsMouse ? Theme.textPrimary : Theme.textSecondary)
                        }

                        Text {
                            text: modelData.name
                            color: root.activeTab === modelData.index ? Theme.primaryLight : (navMouse.containsMouse ? Theme.textPrimary : Theme.textSecondary)
                            font.pixelSize: 12
                            font.weight: root.activeTab === modelData.index ? Font.Bold : Font.Normal
                            Layout.fillWidth: true
                        }
                    }

                    MouseArea {
                        id: navMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.activeTab = modelData.index
                            root.tabSelected(modelData.index)
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }

        // Scraper Engine Bottom Status Pill
        Rectangle {
            Layout.fillWidth: true
            height: 48
            radius: Theme.radiusMd
            color: Theme.surfaceElevated
            border.color: Theme.border

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 8

                Rectangle {
                    width: 8
                    height: 8
                    radius: 4
                    color: Theme.success
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1

                    Text {
                        text: "Scraper Engine"
                        color: Theme.success
                        font.pixelSize: 11
                        font.bold: true
                    }
                    Text {
                        text: "Direct • In-Process"
                        color: Theme.textMuted
                        font.pixelSize: 9
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }

                Rectangle {
                    width: 26
                    height: 26
                    radius: Theme.radiusSm
                    color: reloadMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent"

                    FaIcon {
                        anchors.centerIn: parent
                        icon: Icons.rotate
                        size: 12
                        iconColor: Theme.textMuted
                    }

                    MouseArea {
                        id: reloadMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            Bridge.loadLibrary()
                            Bridge.loadCategories()
                            Bridge.refreshStatus()
                        }
                    }
                }
            }
        }
    }
}
