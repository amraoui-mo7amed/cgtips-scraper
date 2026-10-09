import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "."

Rectangle {
    id: root
    radius: Theme.radiusMd
    color: cardMouse.containsMouse ? Theme.surfaceElevated : Theme.card
    border.color: cardMouse.containsMouse ? Theme.primary : Theme.border
    border.width: 1
    clip: true

    property var itemData: ({})
    signal openGallery(var images, string title)
    signal resolveRequested(string link)
    signal copyRequested(var itemData)
    signal uploadRequested(var itemData)
    signal retryRequested(var itemData)
    signal deleteRequested(var itemData)

    Behavior on color { ColorAnimation { duration: 150 } }
    Behavior on border.color { ColorAnimation { duration: 150 } }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // 3D Model Thumbnail
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 165
            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.1)
            clip: true

            Image {
                id: modelThumb
                anchors.fill: parent
                fillMode: Image.PreserveAspectCrop
                source: {
                    var u = (root.itemData.thumbnail_full || root.itemData.thumbnail || root.itemData.first_image || root.itemData.image_url || "");
                    if (!u) return "";
                    return u.startsWith("http") ? ("image://cgtips/" + encodeURIComponent(u)) : u;
                }
                visible: !!source && status === Image.Ready
                asynchronous: true
                smooth: true
            }

            // Fallback Icon
            FaIcon {
                anchors.centerIn: parent
                visible: !modelThumb.visible
                icon: Icons.cubes
                size: 34
                iconColor: Theme.primaryLight
                opacity: 0.5
            }

            // Top Badges Row
            RowLayout {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 8

                // Left Badge (Category / Image count)
                Rectangle {
                    width: Math.max(26, leftBadgeRow.implicitWidth + 14)
                    height: 22
                    radius: 4
                    color: "#0F172A"
                    border.color: "#334155"
                    border.width: 1
                    clip: true

                    RowLayout {
                        id: leftBadgeRow
                        anchors.centerIn: parent
                        spacing: 5
                        FaIcon {
                            icon: (root.itemData.images_count && root.itemData.images_count > 0) ? Icons.camera : (root.itemData.category ? Icons.tag : Icons.cubes)
                            size: 9
                            iconColor: "#38BDF8"
                        }
                        Text {
                            text: {
                                if (root.itemData.images_count && root.itemData.images_count > 0) return root.itemData.images_count;
                                if (root.itemData.category) return root.itemData.category;
                                return "3D";
                            }
                            color: "#F8FAFC"
                            font.pixelSize: 10
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.maximumWidth: 120
                        }
                    }
                }

                // Provider Badge (Google Drive / Fshare / etc.)
                Rectangle {
                    visible: !!root.itemData.provider
                    height: 22
                    width: Math.max(26, provBadgeRow.implicitWidth + 14)
                    radius: 4
                    color: {
                        var p = (root.itemData.provider || "").toLowerCase();
                        if (p.indexOf("fshare") !== -1) return "#7F1D1D";
                        if (p.indexOf("sharepoint") !== -1) return "#0C4A6E";
                        if (p.indexOf("drive") !== -1 || p.indexOf("gdrive") !== -1) return "#1E3A8A";
                        return "#134E4A";
                    }
                    border.color: {
                        var p = (root.itemData.provider || "").toLowerCase();
                        if (p.indexOf("fshare") !== -1) return "#EF4444";
                        if (p.indexOf("sharepoint") !== -1) return "#0284C7";
                        if (p.indexOf("drive") !== -1 || p.indexOf("gdrive") !== -1) return "#3B82F6";
                        return "#14B8A6";
                    }
                    border.width: 1

                    RowLayout {
                        id: provBadgeRow
                        anchors.centerIn: parent
                        spacing: 5
                        FaIcon {
                            icon: {
                                var p = (root.itemData.provider || "").toLowerCase();
                                if (p.indexOf("fshare") !== -1) return Icons.fire;
                                if (p.indexOf("sharepoint") !== -1) return Icons.cloud;
                                if (p.indexOf("drive") !== -1 || p.indexOf("gdrive") !== -1) return Icons.cloud;
                                return Icons.hdd;
                            }
                            size: 9
                            iconColor: {
                                var p = (root.itemData.provider || "").toLowerCase();
                                if (p.indexOf("fshare") !== -1) return "#FCA5A5";
                                if (p.indexOf("sharepoint") !== -1) return "#38BDF8";
                                if (p.indexOf("drive") !== -1 || p.indexOf("gdrive") !== -1) return "#93C5FD";
                                return "#5EEAD4";
                            }
                        }
                        Text {
                            text: root.itemData.provider || ""
                            color: "#F8FAFC"
                            font.pixelSize: 10
                            font.bold: true
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                // Right Badge (Date or Status / Ready / Missing)
                Rectangle {
                    width: Math.max(90, rightBadgeRow.implicitWidth + 18)
                    height: 22
                    radius: 4
                    color: (root.itemData.folder_path && !root.itemData.has_model) ? Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.25) : "#0F172A"
                    border.color: (root.itemData.folder_path && !root.itemData.has_model) ? Theme.warning : "#334155"
                    border.width: 1

                    RowLayout {
                        id: rightBadgeRow
                        anchors.centerIn: parent
                        spacing: 6
                        FaIcon {
                            icon: root.itemData.published ? Icons.clock : (root.itemData.has_model ? Icons.check : (root.itemData.folder_path ? Icons.exclamationTriangle : Icons.cube))
                            size: 9
                            iconColor: root.itemData.published ? "#94A3B8" : (root.itemData.has_model ? "#10B981" : (root.itemData.folder_path ? Theme.warning : "#94A3B8"))
                        }
                        Text {
                            text: {
                                if (root.itemData.published) {
                                    var p = root.itemData.published.split(" ");
                                    if (p.length >= 4) return p[1] + " " + p[2] + " " + p[3];
                                    if (p.length >= 3) return p[1] + " " + p[2];
                                    return p[0];
                                }
                                if (root.itemData.folder_path && !root.itemData.has_model) return "Missing Model";
                                if (root.itemData.model_size) return root.itemData.model_size;
                                return "SketchUp 3D";
                            }
                            color: (root.itemData.folder_path && !root.itemData.has_model) ? Theme.warning : "#F8FAFC"
                            font.pixelSize: 10
                            font.bold: true
                        }
                    }
                }
            }

            // Click thumbnail to open gallery lightbox
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    var imgs = root.itemData.images_full || (root.itemData.thumbnail_full ? [root.itemData.thumbnail_full] : []);
                    root.openGallery(imgs, root.itemData.title || "");
                }
            }
        }

        // Card Content & Actions
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 12
            spacing: 8

            // Model Title
            Text {
                text: root.itemData.title || "Untitled 3D Model"
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
                wrapMode: Text.Wrap
                maximumLineCount: 2
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Item { Layout.fillHeight: true }

            // Card Actions
            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                // Library Mode Actions (when item has folder_path)
                Item {
                    visible: !!root.itemData.folder_path
                    Layout.fillWidth: true
                    height: 32

                    RowLayout {
                        anchors.fill: parent
                        spacing: 6

                        // Primary Action: Re-download if missing, or Open folder if present
                        Rectangle {
                            Layout.fillWidth: true
                            height: 32
                            radius: Theme.radiusSm
                            color: root.itemData.has_model ? (openFolderMouse.containsMouse ? Theme.surfaceElevated : Theme.card) : (retryMouse.containsMouse ? Theme.warning : Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.2))
                            border.color: root.itemData.has_model ? Theme.border : Theme.warning
                            border.width: 1

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 5
                                FaIcon {
                                    icon: root.itemData.has_model ? Icons.folderOpen : Icons.rotate
                                    size: 10
                                    iconColor: root.itemData.has_model ? Theme.primaryLight : (retryMouse.containsMouse ? "white" : Theme.warning)
                                }
                                Text {
                                    text: root.itemData.has_model ? "Open" : "Re-Download"
                                    color: root.itemData.has_model ? Theme.textPrimary : (retryMouse.containsMouse ? "white" : Theme.warning)
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                id: openFolderMouse
                                visible: root.itemData.has_model
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.openFolder(root.itemData.folder_path)
                            }

                            MouseArea {
                                id: retryMouse
                                visible: !root.itemData.has_model
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    Bridge.retryMissingModel(root.itemData.folder_path)
                                    root.retryRequested(root.itemData)
                                }
                            }
                        }

                        // Copy Article Button
                        Rectangle {
                            width: 32
                            height: 32
                            radius: Theme.radiusSm
                            color: copyArticleMouse.containsMouse ? Theme.surfaceElevated : Theme.card
                            border.color: Theme.border

                            FaIcon {
                                anchors.centerIn: parent
                                icon: Icons.copy
                                size: 10
                                iconColor: Theme.primaryLight
                            }

                            MouseArea {
                                id: copyArticleMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.copyRequested(root.itemData)
                            }
                        }

                        // Upload Article Button
                        Rectangle {
                            width: 32
                            height: 32
                            radius: Theme.radiusSm
                            color: uploadArticleMouse.containsMouse ? Theme.surfaceElevated : Theme.card
                            border.color: Theme.border

                            FaIcon {
                                anchors.centerIn: parent
                                icon: Icons.cloudUpload
                                size: 10
                                iconColor: Theme.primaryLight
                            }

                            MouseArea {
                                id: uploadArticleMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.uploadRequested(root.itemData)
                            }
                        }

                        // Delete Article Button
                        Rectangle {
                            width: 32
                            height: 32
                            radius: Theme.radiusSm
                            color: deleteCardMouse.containsMouse ? Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.2) : Theme.card
                            border.color: deleteCardMouse.containsMouse ? Theme.danger : Theme.border

                            FaIcon {
                                anchors.centerIn: parent
                                icon: Icons.trash
                                size: 10
                                iconColor: deleteCardMouse.containsMouse ? Theme.danger : Theme.textMuted
                            }

                            MouseArea {
                                id: deleteCardMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    Bridge.deleteLibraryModel(root.itemData.folder_path)
                                    root.deleteRequested(root.itemData)
                                }
                            }
                        }
                    }
                }

                // Explore / Feeds Mode Actions (when item does NOT have folder_path)
                Item {
                    visible: !root.itemData.folder_path
                    Layout.fillWidth: true
                    height: 32

                    RowLayout {
                        anchors.fill: parent
                        spacing: 6

                        // Direct Scrape & Download Button
                        Rectangle {
                            Layout.fillWidth: true
                            height: 32
                            radius: Theme.radiusSm
                            color: scrapeMouse.containsMouse ? Theme.primaryHover : Theme.primary

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 6
                                FaIcon {
                                    icon: root.itemData.download_url_full ? Icons.download : Icons.bolt
                                    size: 10
                                    iconColor: "white"
                                }
                                Text {
                                    text: root.itemData.download_url_full ? "Download .zip" : "Scrape"
                                    color: "white"
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }

                            MouseArea {
                                id: scrapeMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (root.itemData.download_url_full) {
                                        Bridge.openExternalUrl(root.itemData.download_url_full);
                                    } else if (root.itemData.link) {
                                        Bridge.resolveArticle(root.itemData.link, true, true);
                                        root.resolveRequested(root.itemData.link);
                                    }
                                }
                            }
                        }

                        // Open Post External Link
                        Rectangle {
                            visible: !!root.itemData.link
                            width: 32
                            height: 32
                            radius: Theme.radiusSm
                            color: openPostMouse.containsMouse ? Theme.surfaceElevated : Theme.card
                            border.color: Theme.border

                            FaIcon {
                                anchors.centerIn: parent
                                icon: Icons.externalLink
                                size: 10
                                iconColor: Theme.textSecondary
                            }

                            MouseArea {
                                id: openPostMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Bridge.openWeb(root.itemData.link)
                            }
                        }

                        // Copy Link Button
                        Rectangle {
                            id: cardCopyBtn
                            visible: !!root.itemData.link
                            property bool isCopied: false
                            Timer {
                                id: cardCopyTimer
                                interval: 2000
                                onTriggered: cardCopyBtn.isCopied = false
                            }
                            width: 32
                            height: 32
                            radius: Theme.radiusSm
                            color: copyPostMouse.containsMouse ? Theme.surfaceElevated : Theme.card
                            border.color: cardCopyBtn.isCopied ? "#10B981" : Theme.border

                            FaIcon {
                                anchors.centerIn: parent
                                icon: cardCopyBtn.isCopied ? Icons.check : Icons.copy
                                size: 10
                                iconColor: cardCopyBtn.isCopied ? "#10B981" : Theme.textSecondary
                            }

                            MouseArea {
                                id: copyPostMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    cardCopyBtn.isCopied = true
                                    cardCopyTimer.restart()
                                    Bridge.copyToClipboard(root.itemData.link || "")
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    MouseArea {
        id: cardMouse
        anchors.fill: parent
        hoverEnabled: true
        propagateComposedEvents: true
    }
}
