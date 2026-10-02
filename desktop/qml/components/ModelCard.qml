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
    // Library items (local folders) get a download status badge and local actions
    readonly property bool isLibrary: root.itemData.folder_path !== undefined
    readonly property bool modelReady: root.isLibrary && !!root.itemData.has_model
    signal openGallery(var images, string title)
    signal resolveRequested(string link)

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

                Item { Layout.fillWidth: true }

                // Library: model download status
                Rectangle {
                    visible: root.isLibrary
                    width: libStatusRow.implicitWidth + 16
                    height: 22
                    radius: 4
                    color: root.modelReady ? "#064E3B" : "#451A03"
                    border.color: root.modelReady ? Theme.success : Theme.warning
                    border.width: 1

                    RowLayout {
                        id: libStatusRow
                        anchors.centerIn: parent
                        spacing: 5
                        FaIcon {
                            icon: root.modelReady ? Icons.checkCircle : Icons.exclamationTriangle
                            size: 9
                            iconColor: root.modelReady ? Theme.success : Theme.warning
                        }
                        Text {
                            text: root.modelReady ? ("Downloaded · " + root.itemData.model_size) : "Model missing"
                            color: "#F8FAFC"
                            font.pixelSize: 10
                            font.bold: true
                        }
                    }
                }

                // Right Badge (Date or Status / Ready)
                Rectangle {
                    visible: !root.isLibrary
                    width: Math.max(90, rightBadgeRow.implicitWidth + 18)
                    height: 22
                    radius: 4
                    color: "#0F172A"
                    border.color: "#334155"
                    border.width: 1

                    RowLayout {
                        id: rightBadgeRow
                        anchors.centerIn: parent
                        spacing: 6
                        FaIcon {
                            icon: root.itemData.published ? Icons.clock : (root.itemData.has_model ? Icons.check : Icons.cube)
                            size: 9
                            iconColor: root.itemData.has_model ? "#10B981" : "#94A3B8"
                        }
                        Text {
                            text: {
                                if (root.itemData.published) {
                                    var p = root.itemData.published.split(" ");
                                    if (p.length >= 4) return p[1] + " " + p[2] + " " + p[3];
                                    if (p.length >= 3) return p[1] + " " + p[2];
                                    return p[0];
                                }
                                if (root.itemData.model_size) return root.itemData.model_size;
                                return "SketchUp 3D";
                            }
                            color: "#F8FAFC"
                            font.pixelSize: 10
                            font.bold: true
                        }
                    }
                }
            }

            // Click thumbnail to open gallery lightbox if available
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

            // Library details line
            Text {
                visible: root.isLibrary
                text: {
                    var parts = [root.itemData.category + " › " + root.itemData.subcategory];
                    parts.push((root.itemData.images_count || 0) + " images");
                    if (root.itemData.imported) parts.push("imported");
                    return parts.join("  ·  ");
                }
                color: Theme.textMuted
                font.pixelSize: 10
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            // Library Actions
            RowLayout {
                visible: root.isLibrary
                Layout.fillWidth: true
                spacing: 6

                ActionButton {
                    Layout.fillWidth: true
                    implicitHeight: 32
                    primary: true
                    text: root.modelReady ? "Open folder" : (root.itemData.article_url ? "Download model" : "Open folder")
                    icon: root.modelReady || !root.itemData.article_url ? Icons.folderOpen : Icons.download
                    onClicked: {
                        if (!root.modelReady && root.itemData.article_url)
                            Bridge.retryLibraryModel(root.itemData.folder_path)
                        else
                            Bridge.openFolder(root.itemData.folder_path)
                    }
                }
                ActionButton {
                    visible: !!root.itemData.article_url
                    implicitHeight: 32
                    icon: Icons.externalLink
                    onClicked: Bridge.openWeb(root.itemData.article_url)
                }
            }

            // Card Actions
            RowLayout {
                visible: !root.isLibrary
                Layout.fillWidth: true
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

    MouseArea {
        id: cardMouse
        anchors.fill: parent
        hoverEnabled: true
        propagateComposedEvents: true
    }
}
