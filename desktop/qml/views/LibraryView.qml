import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "../components"

Item {
    id: root
    signal openGallery(var images, string title)
    property bool moveOnImport: false

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // Filters & Header
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            // Search filter field
            Rectangle {
                Layout.fillWidth: true
                height: 40
                radius: Theme.radiusMd
                color: Theme.surface
                border.color: libFilterInput.activeFocus ? Theme.primary : Theme.border
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 8

                    FaIcon {
                        icon: Icons.search
                        size: 12
                        iconColor: Theme.textMuted
                    }

                    TextInput {
                        id: libFilterInput
                        Layout.fillWidth: true
                        color: Theme.textPrimary
                        font.pixelSize: 12
                        selectByMouse: true
                        clip: true

                        Text {
                            text: "Filter downloaded models by name..."
                            color: Theme.textMuted
                            font.pixelSize: 12
                            visible: !libFilterInput.text && !libFilterInput.activeFocus
                        }

                        onTextChanged: Bridge.loadLibrary(text.trim(), "all")
                    }

                    FaIcon {
                        icon: Icons.times
                        size: 11
                        iconColor: Theme.textMuted
                        visible: libFilterInput.text.length > 0
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                libFilterInput.text = ""
                                Bridge.loadLibrary("", "all")
                            }
                        }
                    }
                }
            }

            // Stats info pill
            Rectangle {
                width: 140
                height: 40
                radius: Theme.radiusMd
                color: Theme.surface
                border.color: Theme.border

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 6
                    FaIcon {
                        icon: Icons.cubes
                        size: 13
                        iconColor: Theme.primaryLight
                    }
                    Text {
                        text: Bridge.libraryTotal + " Models"
                        color: Theme.primaryLight
                        font.pixelSize: 12
                        font.bold: true
                    }
                }
            }

            // Import already-downloaded models
            ActionButton {
                implicitHeight: 40
                text: "Import folder"
                icon: Icons.fileImport
                enabled: !Bridge.maintenanceBusy
                onClicked: Bridge.importLibraryFolder(root.moveOnImport)
            }
            ActionButton {
                implicitHeight: 40
                text: "Import files"
                icon: Icons.upload
                enabled: !Bridge.maintenanceBusy
                onClicked: Bridge.importLibraryFiles(root.moveOnImport)
            }
            ActionButton {
                implicitHeight: 40
                text: root.moveOnImport ? "Moves files" : "Copies files"
                icon: root.moveOnImport ? Icons.squareCheck : Icons.copy
                checked: root.moveOnImport
                onClicked: root.moveOnImport = !root.moveOnImport
            }

            // Open Folder in Finder Button
            Rectangle {
                width: 40
                height: 40
                radius: Theme.radiusMd
                color: Theme.surface
                border.color: Theme.border

                FaIcon {
                    anchors.centerIn: parent
                    icon: Icons.folderOpen
                    size: 13
                    iconColor: Theme.primaryLight
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Bridge.openFolder("")
                }
            }

            // Reload Button
            Rectangle {
                width: 40
                height: 40
                radius: Theme.radiusMd
                color: Theme.surface
                border.color: Theme.border

                FaIcon {
                    anchors.centerIn: parent
                    icon: Icons.rotate
                    size: 13
                    iconColor: Theme.textPrimary
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Bridge.loadLibrary(libFilterInput.text.trim(), "all")
                }
            }
        }

        // Library Items Grid / Empty State
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            BusyIndicator {
                anchors.centerIn: parent
                running: Bridge.libraryLoading || Bridge.maintenanceBusy
                visible: Bridge.libraryLoading || Bridge.maintenanceBusy
            }

            // Empty State
            ColumnLayout {
                anchors.centerIn: parent
                visible: !Bridge.libraryLoading && Bridge.libraryItems.length === 0
                spacing: 12

                FaIcon {
                    icon: Icons.box
                    size: 46
                    iconColor: Theme.border
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "Library is Empty"
                    color: Theme.textPrimary
                    font.pixelSize: 15
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "You haven't downloaded any 3D models yet.\nUse Categories & Feeds, the Direct Resolver or a bulk download —\nor import models you already have with Import folder / Import files."
                    color: Theme.textMuted
                    font.pixelSize: 12
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            // Items Grid
            GridView {
                id: libGrid
                anchors.fill: parent
                visible: !Bridge.libraryLoading && Bridge.libraryItems.length > 0
                clip: true
                cellWidth: Math.floor(libGrid.width / 3)
                cellHeight: 310
                model: Bridge.libraryItems

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }

                delegate: Item {
                    width: libGrid.cellWidth
                    height: libGrid.cellHeight

                    ModelCard {
                        anchors.fill: parent
                        anchors.margins: 7
                        itemData: modelData
                        onOpenGallery: root.openGallery(modelData.images_full, modelData.title)
                    }
                }
            }
        }
    }
}
