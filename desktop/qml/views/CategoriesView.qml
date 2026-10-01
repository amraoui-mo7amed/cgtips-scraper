import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "../components"

Item {
    id: root

    signal openCategoryModalRequested()
    signal resolveRequested(string link)

    property string selectedCategoryName: ""
    property string selectedSubcategoryName: ""
    property string selectedFeedUrl: ""
    property bool isGridView: true
    property bool isFeedCopied: false

    Timer {
        id: feedCopyTimer
        interval: 2000
        onTriggered: root.isFeedCopied = false
    }

    Component.onCompleted: {
        if (Bridge.categories.length === 0) {
            Bridge.loadCategories(false)
        } else {
            root.autoSelectFirstSubcategory()
        }
    }

    Connections {
        target: Bridge
        function onCategoriesChanged() {
            root.autoSelectFirstSubcategory()
        }
    }

    function autoSelectFirstSubcategory() {
        if (Bridge.categories.length > 0 && !root.selectedFeedUrl) {
            var firstCat = Bridge.categories[0];
            if (firstCat && firstCat.subcategories && firstCat.subcategories.length > 0) {
                var firstSub = firstCat.subcategories[0];
                root.selectSubcategory(firstCat.title, firstSub.title, firstSub.feed_url);
            }
        }
    }

    function selectSubcategory(catTitle, subTitle, feedUrl) {
        root.selectedCategoryName = catTitle;
        root.selectedSubcategoryName = subTitle;
        root.selectedFeedUrl = feedUrl;
        if (feedUrl) {
            Bridge.previewFeed(feedUrl);
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14

        // ==========================================
        // COMPACT REDESIGNED HEADER BAR
        // ==========================================
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 56
            Layout.preferredHeight: 56
            radius: Theme.radiusMd
            color: "#0F172A"
            border.color: "#1E293B"
            border.width: 1

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 10

                // Category Picker Trigger Button
                Rectangle {
                    id: catBtn
                    Layout.fillWidth: false
                    Layout.preferredWidth: Math.min(catContentRow.width + 24, 480)
                    Layout.preferredHeight: 40
                    radius: 6
                    color: catBtnMouse.containsMouse ? "#1E293B" : "#131C2E"
                    border.color: catBtnMouse.containsMouse ? "#3B82F6" : "#2A374A"
                    border.width: 1

                    Behavior on color { ColorAnimation { duration: 150 } }
                    Behavior on border.color { ColorAnimation { duration: 150 } }

                    Row {
                        id: catContentRow
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 10

                        Rectangle {
                            width: 28
                            height: 28
                            radius: 6
                            anchors.verticalCenter: parent.verticalCenter
                            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.2)
                            FaIcon {
                                anchors.centerIn: parent
                                icon: Icons.layerGroup
                                size: 13
                                iconColor: Theme.primaryLight
                            }
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 1

                            Text {
                                text: "ACTIVE CATEGORY"
                                color: "#64748B"
                                font.pixelSize: 8
                                font.bold: true
                                font.letterSpacing: 0.5
                            }
                            Text {
                                text: root.selectedCategoryName 
                                    ? (root.selectedCategoryName + "  ›  " + root.selectedSubcategoryName) 
                                    : "Choose Category from Taxonomy Tree..."
                                color: "#F8FAFC"
                                font.pixelSize: 13
                                font.bold: true
                                elide: Text.ElideRight
                                width: Math.min(implicitWidth, 260)
                            }
                        }

                        Rectangle {
                            height: 26
                            width: selectBadgeRow.width + 16
                            radius: 4
                            anchors.verticalCenter: parent.verticalCenter
                            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.15)
                            border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.35)

                            Row {
                                id: selectBadgeRow
                                anchors.centerIn: parent
                                spacing: 6
                                Text {
                                    text: "Change Category"
                                    color: Theme.primaryLight
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                                FaIcon {
                                    icon: Icons.chevronDown
                                    size: 8
                                    iconColor: Theme.primaryLight
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                    }

                    MouseArea {
                        id: catBtnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.openCategoryModalRequested()
                    }
                }

                // Flexible spacer pushing right-hand actions to the right
                Item {
                    Layout.fillWidth: true
                }

                // Refresh Feed Button
                Rectangle {
                    visible: !!root.selectedFeedUrl
                    Layout.preferredHeight: 40
                    Layout.preferredWidth: 40
                    radius: 6
                    color: feedRefreshMouse.containsMouse ? "#1E293B" : "#131C2E"
                    border.color: "#2A374A"

                    FaIcon {
                        anchors.centerIn: parent
                        icon: Icons.rotate
                        size: 13
                        iconColor: Bridge.feedLoading ? Theme.primaryLight : (feedRefreshMouse.containsMouse ? "#F8FAFC" : "#94A3B8")
                        RotationAnimation on rotation {
                            running: Bridge.feedLoading
                            loops: Animation.Infinite
                            from: 0
                            to: 360
                            duration: 1000
                        }
                    }

                    MouseArea {
                        id: feedRefreshMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        enabled: !Bridge.feedLoading
                        onClicked: {
                            if (root.selectedFeedUrl) {
                                Bridge.previewFeed(root.selectedFeedUrl)
                            }
                        }
                    }
                }
            }
        }

        // ==========================================
        // CONTENT AREA (Loading / Empty / Loaded)
        // ==========================================

        // Loading State
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: Bridge.feedLoading

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 16

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: 56
                    height: 56
                    radius: 28
                    color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.12)
                    border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.25)

                    FaIcon {
                        anchors.centerIn: parent
                        icon: Icons.rotate
                        size: 22
                        iconColor: Theme.primaryLight
                        RotationAnimation on rotation {
                            running: Bridge.feedLoading
                            loops: Animation.Infinite
                            from: 0
                            to: 360
                            duration: 1200
                        }
                    }
                }

                ColumnLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 4
                    Text {
                        text: "Fetching Live 3D Models from Feed..."
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: "Resolving Cloudflare network & caching asset thumbnails"
                        color: Theme.textMuted
                        font.pixelSize: 11
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
            }
        }

        // Empty / Placeholder State
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: !Bridge.feedLoading && Bridge.feedItems.length === 0

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 14

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: 68
                    height: 68
                    radius: 34
                    color: Theme.surfaceElevated
                    border.color: Theme.border

                    FaIcon {
                        anchors.centerIn: parent
                        icon: Icons.layerGroup
                        size: 28
                        iconColor: Theme.primaryLight
                    }
                }

                ColumnLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 4
                    Text {
                        text: root.selectedSubcategoryName ? "No models currently found in this feed" : "No Category Selected"
                        color: Theme.textPrimary
                        font.pixelSize: 15
                        font.bold: true
                        Layout.alignment: Qt.AlignHCenter
                    }
                    Text {
                        text: "Select a taxonomy category from the modal tree to explore SketchUp 3D models"
                        color: Theme.textMuted
                        font.pixelSize: 11
                        Layout.alignment: Qt.AlignHCenter
                    }
                }

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: 180
                    height: 38
                    radius: Theme.radiusSm
                    color: Theme.primary

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 8
                        FaIcon {
                            icon: Icons.layerGroup
                            size: 12
                            iconColor: "white"
                        }
                        Text {
                            text: "Browse Categories Tree"
                            color: "white"
                            font.pixelSize: 12
                            font.bold: true
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.openCategoryModalRequested()
                    }
                }
            }
        }

        // ==========================================
        // GRID VIEW (EXACTLY 3 CARDS PER ROW)
        // ==========================================
        GridView {
            id: feedGrid
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            visible: !Bridge.feedLoading && Bridge.feedItems.length > 0
            model: Bridge.feedItems

            // Strictly 3 cards per row:
            cellWidth: Math.floor(feedGrid.width / 3)
            cellHeight: 310

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }

            delegate: Item {
                width: feedGrid.cellWidth
                height: feedGrid.cellHeight

                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 7
                    radius: Theme.radiusMd
                    color: gridMouse.containsMouse ? Theme.surfaceElevated : Theme.card
                    border.color: gridMouse.containsMouse ? Theme.primary : Theme.border
                    border.width: 1
                    clip: true

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
                                source: modelData.image_url ? (modelData.image_url.startsWith("http") ? ("image://cgtips/" + encodeURIComponent(modelData.image_url)) : modelData.image_url) : ""
                                visible: !!modelData.image_url && status === Image.Ready
                                asynchronous: true
                                smooth: true
                            }

                            // Fallback Icon
                            FaIcon {
                                anchors.centerIn: parent
                                visible: !modelData.image_url || modelThumb.status !== Image.Ready
                                icon: Icons.cubes
                                size: 34
                                iconColor: Theme.primaryLight
                                opacity: 0.5
                            }

                            // Top Badges
                            RowLayout {
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.margins: 8

                                // RSS badge
                                Rectangle {
                                    width: 26
                                    height: 22
                                    radius: 4
                                    color: "#0F172A"
                                    border.color: "#334155"
                                    border.width: 1
                                    FaIcon {
                                        anchors.centerIn: parent
                                        icon: Icons.rss
                                        size: 10
                                        iconColor: "#F59E0B"
                                    }
                                }

                                Item { Layout.fillWidth: true }

                                // Date Badge (wide, dark bg, light text)
                                Rectangle {
                                    visible: !!modelData.published
                                    width: Math.max(96, dateBadgeRow.implicitWidth + 18)
                                    height: 22
                                    Layout.preferredWidth: width
                                    Layout.preferredHeight: height
                                    radius: 4
                                    color: "#0F172A"
                                    border.color: "#334155"
                                    border.width: 1

                                    RowLayout {
                                        id: dateBadgeRow
                                        anchors.centerIn: parent
                                        spacing: 6
                                        FaIcon {
                                            icon: Icons.clock
                                            size: 9
                                            iconColor: "#94A3B8"
                                        }
                                        Text {
                                            id: dateText
                                            text: {
                                                if (!modelData.published) return "";
                                                var p = modelData.published.split(" ");
                                                if (p.length >= 4) return p[1] + " " + p[2] + " " + p[3];
                                                if (p.length >= 3) return p[1] + " " + p[2];
                                                return p[0];
                                            }
                                            color: "#F8FAFC"
                                            font.pixelSize: 10
                                            font.bold: true
                                        }
                                    }
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
                                text: modelData.title || "Untitled 3D Model"
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
                                            icon: Icons.bolt
                                            size: 10
                                            iconColor: "white"
                                        }
                                        Text {
                                            text: "Scrape"
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
                                            Bridge.resolveArticle(modelData.link, true, true)
                                            root.resolveRequested(modelData.link)
                                        }
                                    }
                                }

                                // Open Post External Link
                                Rectangle {
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
                                        onClicked: Bridge.openWeb(modelData.link)
                                    }
                                }

                                // Copy Link Button
                                Rectangle {
                                    id: cardCopyBtn
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
                                        iconColor: cardCopyBtn.isCopied ? "#10B981" : (copyPostMouse.containsMouse ? Theme.textPrimary : Theme.textSecondary)
                                    }

                                    MouseArea {
                                        id: copyPostMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            cardCopyBtn.isCopied = true
                                            cardCopyTimer.restart()
                                            Bridge.copyToClipboard(modelData.link)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    MouseArea {
                        id: gridMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.ArrowCursor
                        z: -1
                    }
                }
            }
        }

    }
}
