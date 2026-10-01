import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "../components"

Item {
    id: root
    signal openGallery(var images, string title)
    signal resolveRequested(string link)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // Search Input Box & Quick Chips
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 10

            Rectangle {
                Layout.fillWidth: true
                height: 46
                radius: Theme.radiusMd
                color: Theme.surface
                border.color: exploreInput.activeFocus ? Theme.primary : Theme.border
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    spacing: 10

                    FaIcon {
                        icon: Icons.search
                        size: 14
                        iconColor: Theme.textMuted
                    }

                    TextInput {
                        id: exploreInput
                        Layout.fillWidth: true
                        color: Theme.textPrimary
                        font.pixelSize: 13
                        selectByMouse: true
                        clip: true

                        Text {
                            text: "Search thousands of SketchUp 3D models (e.g. Modern Villa, Luxury Sofa, Dining Chair)..."
                            color: Theme.textMuted
                            font.pixelSize: 13
                            visible: !exploreInput.text && !exploreInput.activeFocus
                        }

                        onAccepted: {
                            if (text.trim().length > 0) {
                                Bridge.performSearch(text.trim(), 1)
                            }
                        }
                    }

                    Rectangle {
                        width: 86
                        height: 32
                        radius: Theme.radiusSm
                        color: Theme.primary

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            FaIcon {
                                icon: Icons.search
                                size: 10
                                iconColor: "white"
                            }
                            Text {
                                text: "Search"
                                color: "white"
                                font.pixelSize: 12
                                font.bold: true
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (exploreInput.text.trim().length > 0) {
                                    Bridge.performSearch(exploreInput.text.trim(), 1)
                                }
                            }
                        }
                    }
                }
            }

            // Quick Keyword Tags
            RowLayout {
                spacing: 8
                Repeater {
                    model: ["Modern Sofa", "Dining Table", "Armchair", "Bed", "Kitchen", "Villa Exterior", "Garden", "Texture"]

                    delegate: Rectangle {
                        height: 28
                        width: tagRow.width + 18
                        radius: 14
                        color: Theme.surfaceElevated
                        border.color: Theme.border

                        Row {
                            id: tagRow
                            anchors.centerIn: parent
                            spacing: 6
                            FaIcon {
                                anchors.verticalCenter: parent.verticalCenter
                                icon: Icons.tag
                                size: 9
                                iconColor: Theme.textMuted
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData
                                color: Theme.textSecondary
                                font.pixelSize: 11
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                exploreInput.text = modelData
                                Bridge.performSearch(modelData, 1)
                            }
                        }
                    }
                }
            }
        }

        // Search Results Content Area
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            BusyIndicator {
                anchors.centerIn: parent
                running: Bridge.isSearching
                visible: Bridge.isSearching
            }

            // Initial Empty Welcome State
            ColumnLayout {
                anchors.centerIn: parent
                visible: !Bridge.isSearching && Bridge.searchResults.length === 0 && !Bridge.searchQuery
                spacing: 12

                FaIcon {
                    icon: Icons.compass
                    size: 46
                    iconColor: Theme.primaryLight
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Explore Remote 3D Models"
                    color: Theme.textPrimary
                    font.pixelSize: 16
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Type keywords above or pick a tag to discover free 3D SketchUp assets from CGTips."
                    color: Theme.textMuted
                    font.pixelSize: 12
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            // No Results State
            ColumnLayout {
                anchors.centerIn: parent
                visible: !Bridge.isSearching && Bridge.searchResults.length === 0 && !!Bridge.searchQuery
                spacing: 10

                FaIcon {
                    icon: Icons.cubes
                    size: 44
                    iconColor: Theme.border
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "No models found"
                    color: Theme.textPrimary
                    font.pixelSize: 15
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Try searching with different terms or check spelling."
                    color: Theme.textMuted
                    font.pixelSize: 12
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            // Results Grid (Strictly 3 cards per row)
            GridView {
                id: resultsGrid
                anchors.fill: parent
                visible: !Bridge.isSearching && Bridge.searchResults.length > 0
                clip: true
                cellWidth: Math.floor(resultsGrid.width / 3)
                cellHeight: 310
                model: Bridge.searchResults

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }

                delegate: Item {
                    width: resultsGrid.cellWidth
                    height: resultsGrid.cellHeight

                    ModelCard {
                        anchors.fill: parent
                        anchors.margins: 7
                        itemData: modelData
                        onOpenGallery: root.openGallery(images, title)
                        onResolveRequested: root.resolveRequested(link)
                    }
                }
            }
        }
    }
}
