import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "../components"

Item {
    id: root
    property bool moveExisting: false
    property bool includeImages: true

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

                            ActionButton {
                                text: "Change..."
                                icon: Icons.folder
                                primary: true
                                enabled: !Bridge.maintenanceBusy && !Bridge.isBulkRunning
                                onClicked: Bridge.chooseStorageDir(root.moveExisting)
                            }
                            ActionButton {
                                text: "Open"
                                icon: Icons.folderOpen
                                onClicked: Bridge.openFolder("")
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        ActionButton {
                            text: "Move existing downloads to the new location"
                            icon: Icons.squareCheck
                            checked: root.moveExisting
                            onClicked: root.moveExisting = !root.moveExisting
                        }
                        Item { Layout.fillWidth: true }
                        Text {
                            text: "Free space: " + (Bridge.statusData.free_space || "—")
                            color: Theme.textMuted
                            font.pixelSize: 11
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: Theme.textMuted
                        font.pixelSize: 11
                        text: "The Library shows whatever is in the storage directory, so you can also point it at a folder "
                            + "you already have (layout: category / sub-category / article / model + images)."
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

            // Download History Card (skip already-downloaded articles on any machine)
            Rectangle {
                Layout.fillWidth: true
                height: historyCol.implicitHeight + 40
                radius: Theme.radiusLg
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                ColumnLayout {
                    id: historyCol
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "Download History"
                            color: Theme.textPrimary
                            font.pixelSize: 15
                            font.bold: true
                            Layout.fillWidth: true
                        }
                        Text {
                            text: Bridge.historyCount + " articles"
                            color: Theme.primaryLight
                            font.pixelSize: 12
                            font.bold: true
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: Theme.textMuted
                        font.pixelSize: 11
                        text: "Articles whose model was already downloaded. Bulk downloads skip them and feed cards show them as "
                            + "Downloaded, even on a computer that doesn't have the files. Export it here and import it on the "
                            + "other computer. Import also accepts the old scraper's selected_feeds.json."
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 10
                        ActionButton {
                            text: "Import history..."
                            icon: Icons.fileImport
                            primary: true
                            enabled: !Bridge.maintenanceBusy
                            onClicked: Bridge.importHistory()
                        }
                        ActionButton {
                            text: "Export history..."
                            icon: Icons.fileExport
                            enabled: !Bridge.maintenanceBusy
                            onClicked: Bridge.exportHistory()
                        }
                    }
                }
            }

            // Cache Backup Card (export / import)
            Rectangle {
                Layout.fillWidth: true
                height: backupCol.implicitHeight + 40
                radius: Theme.radiusLg
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                ColumnLayout {
                    id: backupCol
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14

                    Text {
                        text: "Cache Backup"
                        color: Theme.textPrimary
                        font.pixelSize: 15
                        font.bold: true
                    }
                    Text {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: Theme.textMuted
                        font.pixelSize: 11
                        text: "Export the categories, feed history and thumbnail cache into one .zip, and import it on another "
                            + "machine or after a reinstall so nothing has to be fetched again."
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 10
                        ActionButton {
                            text: "Export cache..."
                            icon: Icons.fileExport
                            primary: true
                            enabled: !Bridge.maintenanceBusy
                            onClicked: Bridge.exportCache(root.includeImages)
                        }
                        ActionButton {
                            text: "Import cache..."
                            icon: Icons.fileImport
                            enabled: !Bridge.maintenanceBusy
                            onClicked: Bridge.importCache()
                        }
                        ActionButton {
                            text: "Include thumbnails"
                            icon: Icons.image
                            checked: root.includeImages
                            onClicked: root.includeImages = !root.includeImages
                        }
                    }

                    Text {
                        visible: Bridge.maintenanceBusy
                        text: Bridge.maintenanceMessage
                        color: Theme.primaryLight
                        font.pixelSize: 11
                        font.bold: true
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
