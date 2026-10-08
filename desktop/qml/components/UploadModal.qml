import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "."

Rectangle {
    id: root
    anchors.fill: parent
    color: "#D9050811"
    z: 9999
    visible: opacity > 0
    opacity: 0

    property string selectedScope: "all"  // "all" | "category" | "subcategory" | "article"
    property string selectedCategory: ""
    property string selectedSubcategory: ""
    property string selectedArticleFolder: ""
    property string selectedArticleTitle: ""

    property var articlesList: []
    property var selectedFolderPaths: []
    property bool copyLogSuccess: false

    Timer {
        id: copyTimer
        interval: 2000
        repeat: false
        onTriggered: root.copyLogSuccess = false
    }

    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

    function refreshArticlesList() {
        var items = Bridge.getUploadArticlesForScope(
            root.selectedScope,
            root.selectedCategory,
            root.selectedSubcategory,
            root.selectedArticleFolder
        ) || [];
        root.articlesList = items;

        var paths = [];
        for (var i = 0; i < items.length; i++) {
            if (items[i].folder_path) {
                paths.push(items[i].folder_path);
            }
        }
        root.selectedFolderPaths = paths;
    }

    function isItemChecked(folderPath) {
        return root.selectedFolderPaths.indexOf(folderPath) !== -1;
    }

    function toggleItem(folderPath) {
        var arr = root.selectedFolderPaths.slice();
        var idx = arr.indexOf(folderPath);
        if (idx !== -1) {
            arr.splice(idx, 1);
        } else {
            arr.push(folderPath);
        }
        root.selectedFolderPaths = arr;
    }

    function toggleAll(selectAll) {
        if (selectAll) {
            var paths = [];
            for (var i = 0; i < root.articlesList.length; i++) {
                paths.push(root.articlesList[i].folder_path);
            }
            root.selectedFolderPaths = paths;
        } else {
            root.selectedFolderPaths = [];
        }
    }

    function copyLogsToClipboard() {
        if (!Bridge.uploadLogs || Bridge.uploadLogs.length === 0) return;
        var text = "";
        for (var i = 0; i < Bridge.uploadLogs.length; i++) {
            text += Bridge.uploadLogs[i] + "\n";
        }
        Bridge.copyToClipboard(text);
        root.copyLogSuccess = true;
        copyTimer.restart();
    }

    onSelectedScopeChanged: {
        if (root.opacity > 0) root.refreshArticlesList();
    }

    onSelectedCategoryChanged: {
        if (uploadCatCombo.model && uploadCatCombo.model.length > 0) {
            var idx = uploadCatCombo.model.indexOf(root.selectedCategory);
            if (idx >= 0) uploadCatCombo.currentIndex = idx;
        }
        if (root.opacity > 0) root.refreshArticlesList();
    }

    onSelectedSubcategoryChanged: {
        if (uploadSubCombo.model && uploadSubCombo.model.length > 0) {
            var idx = uploadSubCombo.model.indexOf(root.selectedSubcategory);
            if (idx >= 0) uploadSubCombo.currentIndex = idx;
        }
        if (root.opacity > 0) root.refreshArticlesList();
    }

    function open(scope, cat, sub, articleFolder, articleTitle) {
        if (scope) root.selectedScope = scope;
        if (cat) root.selectedCategory = cat;
        if (sub) root.selectedSubcategory = sub;
        if (articleFolder) root.selectedArticleFolder = articleFolder;
        if (articleTitle) root.selectedArticleTitle = articleTitle;

        // Auto-select category if none
        if (!root.selectedCategory) {
            if (Bridge.categoryNames && Bridge.categoryNames.length > 0) {
                root.selectedCategory = Bridge.categoryNames[0];
            } else if (Bridge.categories && Bridge.categories.length > 0) {
                root.selectedCategory = Bridge.categories[0].title || Bridge.categories[0].name || "";
            }
        }
        if (!root.selectedSubcategory && root.selectedCategory) {
            var subs = Bridge.getSubcategoriesForCategory(root.selectedCategory);
            if (subs && subs.length > 0) {
                root.selectedSubcategory = subs[0];
            }
        }

        root.refreshArticlesList();
        opacity = 1;
        root.forceActiveFocus();
    }

    function close() {
        if (Bridge.isUploading) {
            Bridge.cancelUpload();
        }
        opacity = 0;
    }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            if (!Bridge.isUploading) {
                root.close();
            }
        }
    }

    Keys.onEscapePressed: {
        if (!Bridge.isUploading) {
            root.close();
        }
    }

    // Modal Card
    Rectangle {
        id: card
        width: Math.min(parent.width - 40, 620)
        implicitHeight: Math.min(cardCol.implicitHeight + 40, parent.height - 40)
        anchors.centerIn: parent
        radius: Theme.radiusLg
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        clip: true

        scale: root.opacity > 0 ? 1.0 : 0.95
        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        ColumnLayout {
            id: cardCol
            anchors.fill: parent
            anchors.margins: 22
            spacing: 16

            // Header Row
            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                Rectangle {
                    width: 40
                    height: 40
                    radius: Theme.radiusMd
                    color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.15)
                    FaIcon {
                        anchors.centerIn: parent
                        icon: Icons.cloudUpload
                        size: 16
                        iconColor: Theme.primaryLight
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: "Upload Articles to Loft Design Gallery"
                        color: Theme.textPrimary
                        font.pixelSize: 15
                        font.bold: true
                    }
                    Text {
                        text: "Publish 3D model articles and rendered photos to https://loftdesign.bilnov.com/api/"
                        color: Theme.textMuted
                        font.pixelSize: 11
                    }
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    width: 28
                    height: 28
                    radius: Theme.radiusSm
                    color: closeMouse.containsMouse ? Theme.surfaceElevated : "transparent"
                    FaIcon {
                        anchors.centerIn: parent
                        icon: Icons.times
                        size: 12
                        iconColor: Theme.textMuted
                    }
                    MouseArea {
                        id: closeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.border
            }

            // Credentials Missing Alert Banner
            Rectangle {
                Layout.fillWidth: true
                height: 42
                radius: Theme.radiusSm
                visible: !Bridge.apiUsername || !Bridge.apiPassword
                color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.15)
                border.color: Theme.warning
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    FaIcon {
                        icon: Icons.exclamationTriangle
                        size: 13
                        iconColor: Theme.warning
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Loft Design API credentials are not configured. Please enter your username and password in Settings."
                        color: Theme.warning
                        font.pixelSize: 11
                        font.bold: true
                        elide: Text.ElideRight
                    }
                }
            }

            // Scope Selector (hidden while uploading)
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: !Bridge.isUploading

                Text {
                    text: "UPLOAD SCOPE"
                    color: Theme.textMuted
                    font.pixelSize: 10
                    font.bold: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    // All Articles Pill
                    Rectangle {
                        Layout.fillWidth: true
                        height: 36
                        radius: Theme.radiusSm
                        color: root.selectedScope === "all" ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.2) : Theme.surfaceElevated
                        border.color: root.selectedScope === "all" ? Theme.primary : Theme.border
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            FaIcon {
                                icon: Icons.cubes
                                size: 11
                                iconColor: root.selectedScope === "all" ? Theme.primaryLight : Theme.textMuted
                            }
                            Text {
                                text: "All Articles (" + Bridge.libraryTotal + ")"
                                color: root.selectedScope === "all" ? Theme.primaryLight : Theme.textSecondary
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.selectedScope = "all"
                        }
                    }

                    // By Category Pill
                    Rectangle {
                        Layout.fillWidth: true
                        height: 36
                        radius: Theme.radiusSm
                        color: root.selectedScope === "category" ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.2) : Theme.surfaceElevated
                        border.color: root.selectedScope === "category" ? Theme.primary : Theme.border
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            FaIcon {
                                icon: Icons.layerGroup
                                size: 11
                                iconColor: root.selectedScope === "category" ? Theme.primaryLight : Theme.textMuted
                            }
                            Text {
                                text: "By Category"
                                color: root.selectedScope === "category" ? Theme.primaryLight : Theme.textSecondary
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.selectedScope = "category"
                        }
                    }

                    // By Subcategory Pill
                    Rectangle {
                        Layout.fillWidth: true
                        height: 36
                        radius: Theme.radiusSm
                        color: root.selectedScope === "subcategory" ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.2) : Theme.surfaceElevated
                        border.color: root.selectedScope === "subcategory" ? Theme.primary : Theme.border
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            FaIcon {
                                icon: Icons.folder
                                size: 11
                                iconColor: root.selectedScope === "subcategory" ? Theme.primaryLight : Theme.textMuted
                            }
                            Text {
                                text: "By Subcategory"
                                color: root.selectedScope === "subcategory" ? Theme.primaryLight : Theme.textSecondary
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.selectedScope = "subcategory"
                        }
                    }

                    // Single Article (if pre-selected)
                    Rectangle {
                        visible: root.selectedScope === "article"
                        Layout.fillWidth: true
                        height: 36
                        radius: Theme.radiusSm
                        color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.2)
                        border.color: Theme.primary
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 6
                            FaIcon {
                                icon: Icons.cube
                                size: 11
                                iconColor: Theme.primaryLight
                            }
                            Text {
                                text: "Single Article"
                                color: Theme.primaryLight
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }
                    }
                }

                // Category & Subcategory dropdowns
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    visible: root.selectedScope === "category" || root.selectedScope === "subcategory"

                    ComboBox {
                        id: uploadCatCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        model: Bridge.categoryNames
                        indicator: Item {}
                        leftPadding: 12
                        rightPadding: 12

                        currentIndex: {
                            if (!model || model.length === 0) return -1;
                            var idx = model.indexOf(root.selectedCategory);
                            return idx >= 0 ? idx : 0;
                        }

                        onActivated: function(index) {
                            var val = model[index];
                            if (val) {
                                root.selectedCategory = val;
                                var subs = Bridge.getSubcategoriesForCategory(val);
                                root.selectedSubcategory = (subs && subs.length > 0) ? subs[0] : "";
                            }
                        }

                        background: Rectangle {
                            implicitHeight: 38
                            radius: Theme.radiusSm
                            color: Theme.surfaceElevated
                            border.color: uploadCatCombo.activeFocus ? Theme.primary : Theme.border
                            border.width: 1
                        }

                        contentItem: RowLayout {
                            spacing: 8

                            FaIcon {
                                icon: Icons.layerGroup
                                size: 11
                                iconColor: Theme.primaryLight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: uploadCatCombo.currentText || root.selectedCategory || "Select Category"
                                color: Theme.textPrimary
                                font.pixelSize: 12
                                font.bold: true
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }

                            FaIcon {
                                icon: Icons.chevronDown
                                size: 9
                                iconColor: Theme.textMuted
                            }
                        }

                        popup: Popup {
                            y: uploadCatCombo.height + 4
                            width: uploadCatCombo.width
                            implicitHeight: Math.min(contentItem.implicitHeight + 16, 220)
                            padding: 6

                            background: Rectangle {
                                radius: Theme.radiusSm
                                color: Theme.surface
                                border.color: Theme.border
                                border.width: 1
                            }

                            contentItem: ListView {
                                clip: true
                                implicitHeight: contentHeight
                                model: uploadCatCombo.popup.visible ? uploadCatCombo.delegateModel : null
                                currentIndex: uploadCatCombo.highlightedIndex
                                ScrollIndicator.vertical: ScrollIndicator {}
                            }
                        }

                        delegate: ItemDelegate {
                            width: uploadCatCombo.width - 12
                            height: 34
                            highlighted: uploadCatCombo.highlightedIndex === index

                            background: Rectangle {
                                radius: 4
                                color: highlighted ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.2) : (hovered ? Theme.surfaceElevated : "transparent")
                            }

                            contentItem: Text {
                                text: modelData
                                color: highlighted ? Theme.primaryLight : Theme.textPrimary
                                font.pixelSize: 11
                                font.bold: highlighted
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 8
                                elide: Text.ElideRight
                            }
                        }
                    }

                    ComboBox {
                        id: uploadSubCombo
                        visible: root.selectedScope === "subcategory"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        model: Bridge.getSubcategoriesForCategory(root.selectedCategory)
                        indicator: Item {}
                        leftPadding: 12
                        rightPadding: 12

                        currentIndex: {
                            if (!model || model.length === 0) return -1;
                            var idx = model.indexOf(root.selectedSubcategory);
                            return idx >= 0 ? idx : 0;
                        }

                        onActivated: function(index) {
                            var val = model[index];
                            if (val) {
                                root.selectedSubcategory = val;
                            }
                        }

                        background: Rectangle {
                            implicitHeight: 38
                            radius: Theme.radiusSm
                            color: Theme.surfaceElevated
                            border.color: uploadSubCombo.activeFocus ? Theme.primary : Theme.border
                            border.width: 1
                        }

                        contentItem: RowLayout {
                            spacing: 8

                            FaIcon {
                                icon: Icons.folder
                                size: 11
                                iconColor: Theme.primaryLight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: uploadSubCombo.currentText || root.selectedSubcategory || "Select Subcategory"
                                color: Theme.textPrimary
                                font.pixelSize: 12
                                font.bold: true
                                elide: Text.ElideRight
                                verticalAlignment: Text.AlignVCenter
                            }

                            FaIcon {
                                icon: Icons.chevronDown
                                size: 9
                                iconColor: Theme.textMuted
                            }
                        }

                        popup: Popup {
                            y: uploadSubCombo.height + 4
                            width: uploadSubCombo.width
                            implicitHeight: Math.min(contentItem.implicitHeight + 16, 220)
                            padding: 6

                            background: Rectangle {
                                radius: Theme.radiusSm
                                color: Theme.surface
                                border.color: Theme.border
                                border.width: 1
                            }

                            contentItem: ListView {
                                clip: true
                                implicitHeight: contentHeight
                                model: uploadSubCombo.popup.visible ? uploadSubCombo.delegateModel : null
                                currentIndex: uploadSubCombo.highlightedIndex
                                ScrollIndicator.vertical: ScrollIndicator {}
                            }
                        }

                        delegate: ItemDelegate {
                            width: uploadSubCombo.width - 12
                            height: 34
                            highlighted: uploadSubCombo.highlightedIndex === index

                            background: Rectangle {
                                radius: 4
                                color: highlighted ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.2) : (hovered ? Theme.surfaceElevated : "transparent")
                            }

                            contentItem: Text {
                                text: modelData
                                color: highlighted ? Theme.primaryLight : Theme.textPrimary
                                font.pixelSize: 11
                                font.bold: highlighted
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 8
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            // Article Selection List Header (hidden while uploading)
            RowLayout {
                Layout.fillWidth: true
                visible: !Bridge.isUploading
                spacing: 8

                Text {
                    text: "ARTICLES TO UPLOAD (" + root.selectedFolderPaths.length + " of " + root.articlesList.length + " selected)"
                    color: Theme.textMuted
                    font.pixelSize: 10
                    font.bold: true
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: "Select All"
                    color: Theme.primaryLight
                    font.pixelSize: 11
                    font.bold: true
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.toggleAll(true)
                    }
                }

                Text {
                    text: "•"
                    color: Theme.textMuted
                    font.pixelSize: 11
                }

                Text {
                    text: "Deselect All"
                    color: Theme.textMuted
                    font.pixelSize: 11
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.toggleAll(false)
                    }
                }
            }

            // Articles Selection ListView (hidden while uploading)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 180
                Layout.maximumHeight: 220
                visible: !Bridge.isUploading
                radius: Theme.radiusSm
                color: "#080C14"
                border.color: Theme.border
                border.width: 1
                clip: true

                Text {
                    anchors.centerIn: parent
                    visible: root.articlesList.length === 0
                    text: "No articles found matching this scope."
                    color: Theme.textMuted
                    font.pixelSize: 12
                }

                ListView {
                    id: articlesListView
                    anchors.fill: parent
                    anchors.margins: 6
                    model: root.articlesList
                    clip: true
                    spacing: 6
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollIndicator.vertical: ScrollIndicator {}

                    delegate: Rectangle {
                        width: articlesListView.width
                        height: 52
                        radius: Theme.radiusSm
                        color: root.isItemChecked(modelData.folder_path) ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.12) : Theme.card
                        border.color: root.isItemChecked(modelData.folder_path) ? Theme.primary : Theme.border
                        border.width: 1

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.toggleItem(modelData.folder_path)
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 10

                            // Checkbox
                            Rectangle {
                                width: 18
                                height: 18
                                radius: 4
                                color: root.isItemChecked(modelData.folder_path) ? Theme.primary : "transparent"
                                border.color: root.isItemChecked(modelData.folder_path) ? Theme.primary : Theme.border
                                border.width: 1

                                FaIcon {
                                    anchors.centerIn: parent
                                    visible: root.isItemChecked(modelData.folder_path)
                                    icon: Icons.check
                                    size: 9
                                    iconColor: "white"
                                }
                            }

                            // Thumbnail
                            Rectangle {
                                width: 36
                                height: 36
                                radius: 4
                                color: "#0B111E"
                                clip: true

                                Image {
                                    anchors.fill: parent
                                    source: modelData.first_image || ""
                                    fillMode: Image.PreserveAspectCrop
                                    asynchronous: true
                                    cache: true
                                }

                                FaIcon {
                                    anchors.centerIn: parent
                                    visible: !modelData.first_image
                                    icon: Icons.cube
                                    size: 14
                                    iconColor: Theme.textMuted
                                }
                            }

                            // Info Column
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.title
                                    color: Theme.textPrimary
                                    font.pixelSize: 12
                                    font.bold: true
                                    elide: Text.ElideRight
                                }

                                RowLayout {
                                    spacing: 8
                                    Text {
                                        text: (modelData.category || "General") + " • " + (modelData.subcategory || "General")
                                        color: Theme.textSecondary
                                        font.pixelSize: 10
                                    }

                                    Text {
                                        text: "• " + (modelData.images_count || (modelData.images && modelData.images.length) || 0) + " photos"
                                        color: Theme.primaryLight
                                        font.pixelSize: 10
                                        font.bold: true
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Upload Progress Section (visible when uploading)
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: Bridge.isUploading

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "UPLOADING TO LOFT DESIGN (" + Bridge.uploadProgress.current + " of " + Bridge.uploadProgress.total + ")"
                        color: Theme.primaryLight
                        font.pixelSize: 11
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: Math.round(Bridge.uploadProgress.percent || 0) + "%"
                        color: Theme.primaryLight
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                // Progress Bar
                Rectangle {
                    Layout.fillWidth: true
                    height: 8
                    radius: 4
                    color: Theme.surfaceElevated
                    clip: true

                    Rectangle {
                        height: parent.height
                        width: parent.width * Math.min(Math.max((Bridge.uploadProgress.percent || 0) / 100.0, 0.0), 1.0)
                        radius: 4
                        color: Theme.primary

                        Behavior on width { NumberAnimation { duration: 250 } }
                    }
                }

                Text {
                    text: Bridge.uploadProgress.status || "Publishing articles..."
                    color: Theme.textSecondary
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            // Live Log Console Box (visible when uploading or logs exist)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                visible: Bridge.isUploading || (Bridge.uploadLogs && Bridge.uploadLogs.length > 0)
                radius: Theme.radiusSm
                color: "#080C14"
                border.color: Theme.border
                clip: true

                ListView {
                    id: logList
                    anchors.fill: parent
                    anchors.margins: 8
                    model: Bridge.uploadLogs
                    clip: true

                    delegate: Text {
                        width: logList.width
                        text: modelData
                        color: modelData.indexOf("✓") !== -1 ? "#10B981" : (modelData.indexOf("✗") !== -1 ? "#EF4444" : (modelData.indexOf("===") !== -1 ? Theme.primaryLight : "#94A3B8"))
                        font.pixelSize: 10
                        font.family: "Menlo, Monaco, 'Courier New', monospace"
                        wrapMode: Text.Wrap
                    }

                    onCountChanged: {
                        Qt.callLater(function() {
                            logList.positionViewAtEnd();
                        })
                    }
                }
            }

            // Footer Actions
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                // Copy Log Button
                Rectangle {
                    id: copyLogBtn
                    height: 38
                    implicitWidth: copyRow.implicitWidth + 24
                    radius: Theme.radiusSm
                    color: copyMouse.containsMouse ? Theme.surfaceHover : Theme.surfaceElevated
                    border.color: root.copyLogSuccess ? "#10B981" : Theme.border
                    opacity: (Bridge.uploadLogs && Bridge.uploadLogs.length > 0) ? 1.0 : 0.4

                    RowLayout {
                        id: copyRow
                        anchors.centerIn: parent
                        spacing: 6
                        FaIcon {
                            icon: root.copyLogSuccess ? Icons.check : Icons.copy
                            size: 11
                            iconColor: root.copyLogSuccess ? "#10B981" : (copyMouse.containsMouse ? Theme.textPrimary : Theme.textSecondary)
                        }
                        Text {
                            text: root.copyLogSuccess ? "Copied!" : "Copy Log"
                            color: root.copyLogSuccess ? "#10B981" : (copyMouse.containsMouse ? Theme.textPrimary : Theme.textSecondary)
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: copyMouse
                        anchors.fill: parent
                        enabled: Bridge.uploadLogs && Bridge.uploadLogs.length > 0
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.copyLogsToClipboard()
                    }
                }

                Item { Layout.fillWidth: true }

                // Stop / Cancel Button (when uploading)
                Rectangle {
                    visible: Bridge.isUploading
                    height: 38
                    implicitWidth: cancelRow.implicitWidth + 24
                    radius: Theme.radiusSm
                    color: cancelMouse.containsMouse ? Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.25) : Theme.surfaceElevated
                    border.color: Theme.danger
                    border.width: 1

                    RowLayout {
                        id: cancelRow
                        anchors.centerIn: parent
                        spacing: 6
                        FaIcon {
                            icon: Icons.stop
                            size: 11
                            iconColor: Theme.danger
                        }
                        Text {
                            text: "Stop Upload"
                            color: Theme.danger
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: cancelMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Bridge.cancelUpload()
                    }
                }

                // Close Button (when not uploading)
                Rectangle {
                    visible: !Bridge.isUploading
                    height: 38
                    implicitWidth: 80
                    radius: Theme.radiusSm
                    color: closeBtnMouse.containsMouse ? Theme.surfaceHover : Theme.surfaceElevated
                    border.color: Theme.border

                    Text {
                        anchors.centerIn: parent
                        text: "Close"
                        color: Theme.textSecondary
                        font.pixelSize: 11
                        font.bold: true
                    }

                    MouseArea {
                        id: closeBtnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }

                // Start Upload Button (when not uploading)
                Rectangle {
                    visible: !Bridge.isUploading
                    height: 38
                    implicitWidth: startRow.implicitWidth + 28
                    radius: Theme.radiusSm
                    color: root.selectedFolderPaths.length > 0 ? (startMouse.containsMouse ? Qt.darker(Theme.primary, 1.1) : Theme.primary) : Theme.surfaceElevated
                    border.color: root.selectedFolderPaths.length > 0 ? Theme.primary : Theme.border
                    opacity: root.selectedFolderPaths.length > 0 ? 1.0 : 0.5

                    RowLayout {
                        id: startRow
                        anchors.centerIn: parent
                        spacing: 8
                        FaIcon {
                            icon: Icons.cloudUpload
                            size: 12
                            iconColor: root.selectedFolderPaths.length > 0 ? "white" : Theme.textMuted
                        }
                        Text {
                            text: "Upload " + root.selectedFolderPaths.length + " Article" + (root.selectedFolderPaths.length === 1 ? "" : "s")
                            color: root.selectedFolderPaths.length > 0 ? "white" : Theme.textMuted
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: startMouse
                        anchors.fill: parent
                        enabled: root.selectedFolderPaths.length > 0
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            Bridge.uploadArticlesList(root.selectedFolderPaths);
                        }
                    }
                }
            }
        }
    }
}
