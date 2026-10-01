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
