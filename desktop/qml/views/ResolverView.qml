import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "../components"

Item {
    id: root

    function setUrl(url) {
        urlInput.text = url
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

            // Resolver Card
            Rectangle {
                Layout.fillWidth: true
                height: resolverCol.implicitHeight + 40
                radius: Theme.radiusLg
                color: Theme.surface
                border.color: Theme.border
                border.width: 1

                ColumnLayout {
                    id: resolverCol
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
                                icon: Icons.bolt
                                size: 18
                                iconColor: Theme.primaryLight
                            }
                        }
                        ColumnLayout {
                            spacing: 2
                            Text {
                                text: "Direct Locker Bypass & Downloader"
                                color: Theme.textPrimary
                                font.pixelSize: 15
                                font.bold: true
                            }
                            Text {
                                text: "Paste any CGTips post URL to download 3D models and images on-demand"
                                color: Theme.textMuted
                                font.pixelSize: 11
                            }
                        }
                    }

                    // Input Box
                    Rectangle {
                        Layout.fillWidth: true
                        height: 46
                        radius: Theme.radiusMd
                        color: Theme.surfaceElevated
                        border.color: urlInput.activeFocus ? Theme.primary : Theme.border
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            FaIcon {
                                icon: Icons.link
                                size: 13
                                iconColor: Theme.textMuted
                            }

                            TextInput {
                                id: urlInput
                                Layout.fillWidth: true
                                color: Theme.textPrimary
                                font.pixelSize: 13
                                selectByMouse: true
                                clip: true

                                Text {
                                    text: "https://sketchup.cgtips.org/post-name-slug/"
                                    color: Theme.textMuted
                                    font.pixelSize: 13
                                    visible: !urlInput.text && !urlInput.activeFocus
                                }

                                onAccepted: resolveBtn.triggerResolve()
                            }

                            FaIcon {
                                icon: Icons.times
                                size: 11
                                iconColor: Theme.textMuted
                                visible: urlInput.text.length > 0
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: urlInput.text = ""
                                }
                            }
                        }
                    }

                    // Checkboxes and Trigger Button
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 20

                        CheckBox {
                            id: chkDlModel
                            checked: true
                            text: "Download 3D Model (.zip)"
                        }

                        CheckBox {
                            id: chkDlImages
                            checked: true
                            text: "Download Full-Res Photos"
                        }

                        Item { Layout.fillWidth: true }

                        Rectangle {
                            id: resolveBtn
                            width: 180
                            height: 38
                            radius: Theme.radiusMd
                            color: Bridge.isResolving ? Theme.surfaceElevated : Theme.primary

                            function triggerResolve() {
                                if (urlInput.text.trim().length > 0 && !Bridge.isResolving) {
                                    Bridge.resolveArticle(urlInput.text.trim(), chkDlModel.checked, chkDlImages.checked)
                                }
                            }

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 8

                                BusyIndicator {
                                    width: 18
                                    height: 18
                                    running: Bridge.isResolving
                                    visible: Bridge.isResolving
                                }

                                FaIcon {
                                    visible: !Bridge.isResolving
                                    icon: Icons.bolt
                                    size: 12
                                    iconColor: "white"
                                }

                                Text {
                                    text: Bridge.isResolving ? "Resolving..." : "Resolve & Download"
                                    color: "white"
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                enabled: !Bridge.isResolving
                                onClicked: resolveBtn.triggerResolve()
                            }
                        }
                    }
                }
            }

            // Results Card (Shown when resolverResult is available)
            Rectangle {
                Layout.fillWidth: true
                visible: !!Bridge.resolverResult.title || !!Bridge.resolverResult.model_filename
                height: resultCol.implicitHeight + 40
                radius: Theme.radiusLg
                color: Theme.surface
                border.color: Theme.success
                border.width: 1

                ColumnLayout {
                    id: resultCol
                    anchors.fill: parent
                    anchors.margins: 20
                    spacing: 14

                    RowLayout {
                        spacing: 8
                        FaIcon {
                            icon: Icons.checkCircle
                            size: 16
                            iconColor: Theme.success
                        }
                        Text {
                            text: "Resolution Complete!"
                            color: Theme.success
                            font.pixelSize: 14
                            font.bold: true
                        }
                    }

                    Text {
                        text: Bridge.resolverResult.title || "Model Downloaded"
                        color: Theme.textPrimary
                        font.pixelSize: 15
                        font.bold: true
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.border
                    }

                    // Specs Grid
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 24

                        ColumnLayout {
                            spacing: 4
                            Text { text: "ARCHIVE SIZE"; color: Theme.textMuted; font.pixelSize: 9; font.bold: true }
                            Text { text: Bridge.resolverResult.model_size || "Ready"; color: Theme.primaryLight; font.pixelSize: 13; font.bold: true }
                        }

                        ColumnLayout {
                            spacing: 4
                            Text { text: "PREVIEW IMAGES"; color: Theme.textMuted; font.pixelSize: 9; font.bold: true }
                            Text { text: (Bridge.resolverResult.images_count || 0) + " photos saved"; color: Theme.textPrimary; font.pixelSize: 13; font.bold: true }
                        }

                        ColumnLayout {
                            spacing: 4
                            Text { text: "STATUS"; color: Theme.textMuted; font.pixelSize: 9; font.bold: true }
                            Text { text: "Saved to Library"; color: Theme.success; font.pixelSize: 13; font.bold: true }
                        }
                    }

                    // Buttons
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Rectangle {
                            height: 38
                            Layout.fillWidth: true
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
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.openFolder("Direct_Downloads")
                            }
                        }

                        Rectangle {
                            visible: !!Bridge.resolverResult.gdrive_url
                            height: 38
                            width: 150
                            radius: Theme.radiusSm
                            color: Theme.surfaceElevated
                            border.color: Theme.border

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                Text {
                                    text: "Google Drive"
                                    color: Theme.textSecondary
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                                FaIcon {
                                    icon: Icons.externalLink
                                    size: 10
                                    iconColor: Theme.textSecondary
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.openWeb(Bridge.resolverResult.gdrive_url)
                            }
                        }
                    }
                }
            }

            // Live Resolver Progress Log Box
            Rectangle {
                Layout.fillWidth: true
                visible: Bridge.isResolving || (Bridge.resolverLogs && Bridge.resolverLogs.length > 0)
                height: 180
                radius: Theme.radiusMd
                color: "#080C14"
                border.color: Theme.border
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    RowLayout {
                        spacing: 8
                        FaIcon {
                            icon: Icons.terminal
                            size: 11
                            iconColor: Theme.primaryLight
                        }
                        Text {
                            text: "Scraper Live Activity"
                            color: Theme.textMuted
                            font.pixelSize: 10
                            font.bold: true
                        }
                        Item { Layout.fillWidth: true }
                        BusyIndicator {
                            width: 14
                            height: 14
                            running: Bridge.isResolving
                            visible: Bridge.isResolving
                        }
                    }

                    ListView {
                        id: logList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: Bridge.resolverLogs
                        delegate: Text {
                            text: modelData
                            color: Theme.textSecondary
                            font.pixelSize: 10
                            font.family: "Menlo"
                            wrapMode: Text.Wrap
                            width: logList.width
                        }
                        onCountChanged: {
                            positionViewAtEnd()
                        }
                    }
                }
            }
        }
    }
}
