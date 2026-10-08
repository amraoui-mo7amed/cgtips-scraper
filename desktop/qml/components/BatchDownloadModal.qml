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

    property var missingItemsList: []
    property var selectedFolderPaths: []
    property bool copyLogSuccess: false

    Timer {
        id: copyTimer
        interval: 2000
        repeat: false
        onTriggered: root.copyLogSuccess = false
    }

    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

    function refreshMissingList() {
        var items = Bridge.getMissingModelsForScope(
            root.selectedScope,
            root.selectedCategory,
            root.selectedSubcategory,
            root.selectedArticleFolder
        ) || [];
        root.missingItemsList = items;

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
            for (var i = 0; i < root.missingItemsList.length; i++) {
                paths.push(root.missingItemsList[i].folder_path);
            }
            root.selectedFolderPaths = paths;
        } else {
            root.selectedFolderPaths = [];
        }
    }

    onSelectedScopeChanged: {
        if (root.opacity > 0) root.refreshMissingList();
    }

    onSelectedCategoryChanged: {
        if (catCombo.model && catCombo.model.length > 0) {
            var idx = catCombo.model.indexOf(root.selectedCategory);
            if (idx >= 0) catCombo.currentIndex = idx;
        }
        if (root.opacity > 0) root.refreshMissingList();
    }

    onSelectedSubcategoryChanged: {
        if (subCombo.model && subCombo.model.length > 0) {
            var idx = subCombo.model.indexOf(root.selectedSubcategory);
            if (idx >= 0) subCombo.currentIndex = idx;
        }
        if (root.opacity > 0) root.refreshMissingList();
    }

    Connections {
        target: Bridge
        function onIsBatchDownloadingChanged() {
            if (!Bridge.isBatchDownloading && root.opacity > 0) {
                root.refreshMissingList();
            }
        }
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

        root.refreshMissingList();

        opacity = 1
        root.forceActiveFocus()
    }

    function close() {
        if (Bridge.isBatchDownloading) {
            Bridge.cancelBatchDownload()
        }
        opacity = 0
    }

    // Dismiss on backdrop click only if not actively downloading
    MouseArea {
        anchors.fill: parent
        onClicked: {
            if (!Bridge.isBatchDownloading) {
                root.close()
            }
        }
    }

    Keys.onEscapePressed: {
        if (!Bridge.isBatchDownloading) {
            root.close()
        }
    }

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

            // Header
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
                        icon: Icons.download
                        size: 16
                        iconColor: Theme.primaryLight
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: "Re-Download Missing Models"
                        color: Theme.textPrimary
                        font.pixelSize: 15
                        font.bold: true
                    }
                    Text {
                        text: "Bypasses countdown lockers and re-fetches 3D model archives"
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

            // Scope Selector (visible when NOT running)
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: !Bridge.isBatchDownloading

                Text {
                    text: "DOWNLOAD SCOPE"
                    color: Theme.textMuted
                    font.pixelSize: 10
                    font.bold: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    // All Missing Pill
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
                                text: "All Missing (" + Bridge.missingModelsCount + ")"
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
                                text: "Selected Article"
                                color: Theme.primaryLight
                                font.pixelSize: 11
                                font.bold: true
                            }
                        }
                    }
                }

                // Category dropdown / selector when scope is category or subcategory
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    visible: root.selectedScope === "category" || root.selectedScope === "subcategory"

                    ComboBox {
                        id: catCombo
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
                            border.color: catCombo.activeFocus ? Theme.primary : Theme.border
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
                                text: catCombo.currentText || root.selectedCategory || "Select Category"
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
                            y: catCombo.height + 4
                            width: catCombo.width
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
                                model: catCombo.popup.visible ? catCombo.delegateModel : null
                                currentIndex: catCombo.highlightedIndex
                                ScrollIndicator.vertical: ScrollIndicator {}
                            }
                        }

                        delegate: ItemDelegate {
                            width: catCombo.width - 12
                            height: 34
                            highlighted: catCombo.highlightedIndex === index

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
                        id: subCombo
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
                            border.color: subCombo.activeFocus ? Theme.primary : Theme.border
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
                                text: subCombo.currentText || root.selectedSubcategory || "Select Subcategory"
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
                            y: subCombo.height + 4
                            width: subCombo.width
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
                                model: subCombo.popup.visible ? subCombo.delegateModel : null
                                currentIndex: subCombo.highlightedIndex
                                ScrollIndicator.vertical: ScrollIndicator {}
                            }
                        }

                        delegate: ItemDelegate {
                            width: subCombo.width - 12
                            height: 34
                            highlighted: subCombo.highlightedIndex === index

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

                // Article title preview when scope is article
                Rectangle {
                    visible: root.selectedScope === "article"
                    Layout.fillWidth: true
                    height: 38
                    radius: Theme.radiusSm
                    color: Theme.surfaceElevated
                    border.color: Theme.border

                    Text {
                        anchors.fill: parent
                        anchors.margins: 10
                        text: root.selectedArticleTitle || root.selectedArticleFolder
                        color: Theme.textPrimary
                        font.pixelSize: 11
                        font.bold: true
                        elide: Text.ElideRight
                    }
                }
            }

            // Filtered Missing Models Checklist Section (visible when NOT downloading)
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: !Bridge.isBatchDownloading

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        text: "FILTERED MISSING MODELS (" + root.selectedFolderPaths.length + " / " + root.missingItemsList.length + " SELECTED)"
                        color: Theme.textMuted
                        font.pixelSize: 10
                        font.bold: true
                    }

                    Item { Layout.fillWidth: true }

                    // Select All / Deselect All Button
                    Rectangle {
                        visible: root.missingItemsList.length > 0
                        width: 76
                        height: 24
                        radius: 4
                        color: selAllMouse.containsMouse ? Theme.surfaceElevated : "transparent"
                        border.color: Theme.border
                        border.width: 1

                        Text {
                            anchors.centerIn: parent
                            text: root.selectedFolderPaths.length === root.missingItemsList.length ? "Deselect All" : "Select All"
                            color: Theme.primaryLight
                            font.pixelSize: 10
                            font.bold: true
                        }

                        MouseArea {
                            id: selAllMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.selectedFolderPaths.length === root.missingItemsList.length) {
                                    root.toggleAll(false);
                                } else {
                                    root.toggleAll(true);
                                }
                            }
                        }
                    }
                }

                // Scrollable Checklist Card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    Layout.maximumHeight: 220
                    radius: Theme.radiusSm
                    color: "#080C14"
                    border.color: Theme.border
                    border.width: 1
                    clip: true

                    // Empty state when 0 missing items
                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 8
                        visible: root.missingItemsList.length === 0

                        FaIcon {
                            Layout.alignment: Qt.AlignHCenter
                            icon: Icons.checkCircle
                            size: 24
                            iconColor: "#10B981"
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "No missing models found in this scope!"
                            color: Theme.textPrimary
                            font.pixelSize: 12
                            font.bold: true
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "All 3D models here are already downloaded and complete."
                            color: Theme.textMuted
                            font.pixelSize: 11
                        }
                    }

                    ListView {
                        id: missingCheckList
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 4
                        clip: true
                        model: root.missingItemsList
                        visible: root.missingItemsList.length > 0
                        ScrollIndicator.vertical: ScrollIndicator {}

                        delegate: Rectangle {
                            width: missingCheckList.width
                            height: 44
                            radius: 6
                            color: itemHover.containsMouse ? Theme.surfaceElevated : (root.isItemChecked(modelData.folder_path) ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.08) : "#0F1522")
                            border.color: root.isItemChecked(modelData.folder_path) ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.4) : Theme.border
                            border.width: 1

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
                                        size: 10
                                        iconColor: "white"
                                    }
                                }

                                // Thumbnail preview
                                Rectangle {
                                    width: 32
                                    height: 32
                                    radius: 4
                                    color: "#1E293B"
                                    clip: true

                                    Image {
                                        anchors.fill: parent
                                        source: modelData.first_image || ""
                                        fillMode: Image.PreserveAspectCrop
                                        visible: !!modelData.first_image
                                    }

                                    FaIcon {
                                        anchors.centerIn: parent
                                        visible: !modelData.first_image
                                        icon: Icons.cube
                                        size: 12
                                        iconColor: Theme.textMuted
                                    }
                                }

                                // Title and category
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.title || ""
                                        color: Theme.textPrimary
                                        font.pixelSize: 11
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: (modelData.category || "") + " • " + (modelData.subcategory || "")
                                        color: Theme.textMuted
                                        font.pixelSize: 10
                                        elide: Text.ElideRight
                                    }
                                }

                                // Missing badge
                                Rectangle {
                                    width: 90
                                    height: 22
                                    radius: 4
                                    color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.15)
                                    border.color: Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.4)
                                    border.width: 1

                                    RowLayout {
                                        anchors.centerIn: parent
                                        spacing: 4
                                        FaIcon {
                                            icon: Icons.exclamationTriangle
                                            size: 9
                                            iconColor: Theme.warning
                                        }
                                        Text {
                                            text: "Missing Model"
                                            color: Theme.warning
                                            font.pixelSize: 9
                                            font.bold: true
                                        }
                                    }
                                }
                            }

                            MouseArea {
                                id: itemHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.toggleItem(modelData.folder_path)
                            }
                        }
                    }
                }
            }

            // Active Progress & Status (visible when downloading)
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: Bridge.isBatchDownloading

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "DOWNLOADING PROGRESS"
                        color: Theme.textMuted
                        font.pixelSize: 10
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: Math.round(Bridge.batchDownloadProgress.percent || 0) + "%"
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
                        width: parent.width * Math.min(Math.max((Bridge.batchDownloadProgress.percent || 0) / 100.0, 0.0), 1.0)
                        radius: 4
                        color: Theme.primary

                        Behavior on width { NumberAnimation { duration: 250 } }
                    }
                }

                Text {
                    text: Bridge.batchDownloadProgress.status || "Downloading 3D models..."
                    color: Theme.textSecondary
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            // Live Log Console Box (visible when downloading or logs exist)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                visible: Bridge.isBatchDownloading || (Bridge.batchDownloadLogs && Bridge.batchDownloadLogs.length > 0)
                radius: Theme.radiusSm
                color: "#080C14"
                border.color: Theme.border
                clip: true

                ListView {
                    id: logList
                    anchors.fill: parent
                    anchors.margins: 8
                    model: Bridge.batchDownloadLogs
                    clip: true

                    delegate: Text {
                        width: logList.width
                        text: modelData
                        color: modelData.indexOf("✓") !== -1 ? "#10B981" : (modelData.indexOf("✗") !== -1 ? "#EF4444" : "#94A3B8")
                        font.pixelSize: 10
                        font.family: "Menlo, Monaco, 'Courier New', monospace"
                        wrapMode: Text.Wrap
                    }

                    onCountChanged: {
                        Qt.callLater(function() {
                            logList.positionViewAtEnd()
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
                    height: 36
                    implicitWidth: copyRow.implicitWidth + 24
                    radius: Theme.radiusSm
                    color: copyMouse.containsMouse ? Theme.surfaceHover : Theme.surfaceElevated
                    border.color: root.copyLogSuccess ? "#10B981" : Theme.border
                    opacity: (Bridge.batchDownloadLogs && Bridge.batchDownloadLogs.length > 0) ? 1.0 : 0.4

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
                        hoverEnabled: Bridge.batchDownloadLogs && Bridge.batchDownloadLogs.length > 0
                        cursorShape: (Bridge.batchDownloadLogs && Bridge.batchDownloadLogs.length > 0) ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: {
                            if (Bridge.batchDownloadLogs && Bridge.batchDownloadLogs.length > 0) {
                                var logs = Bridge.batchDownloadLogs;
                                var text = logs.join("\n");
                                Bridge.copyToClipboard(text);
                                root.copyLogSuccess = true;
                                copyTimer.restart();
                            }
                        }
                    }

                    ToolTip.visible: copyMouse.containsMouse && Bridge.batchDownloadLogs && Bridge.batchDownloadLogs.length > 0
                    ToolTip.delay: 500
                    ToolTip.text: "Copy download logs to clipboard"
                }

                // Auto-Retry Toggle Button
                Rectangle {
                    id: autoRetryBtn
                    height: 36
                    implicitWidth: retryRow.implicitWidth + 24
                    radius: Theme.radiusSm
                    color: Bridge.autoRetryEnabled
                           ? Qt.rgba(0.06, 0.72, 0.51, 0.18)
                           : (autoRetryMouse.containsMouse ? Theme.surfaceHover : Theme.surfaceElevated)
                    border.color: Bridge.autoRetryEnabled ? "#10B981" : Theme.border

                    RowLayout {
                        id: retryRow
                        anchors.centerIn: parent
                        spacing: 6
                        FaIcon {
                            icon: Icons.sync
                            size: 11
                            iconColor: Bridge.autoRetryEnabled ? "#10B981" : Theme.textSecondary
                        }
                        Text {
                            text: Bridge.autoRetryEnabled ? "Auto-Retry: ON" : "Auto-Retry: OFF"
                            color: Bridge.autoRetryEnabled ? "#10B981" : Theme.textSecondary
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: autoRetryMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            Bridge.toggleAutoRetry();
                        }
                    }

                    ToolTip.visible: autoRetryMouse.containsMouse
                    ToolTip.delay: 500
                    ToolTip.text: Bridge.autoRetryEnabled
                        ? "Auto-retry is ON: continuously retries failed downloads until all complete."
                        : "Click to enable auto-retry: automatically retries until all models are downloaded."
                }

                Item { Layout.fillWidth: true }

                // Cancel Button (when active)
                Rectangle {
                    visible: Bridge.isBatchDownloading
                    width: 100
                    height: 36
                    radius: Theme.radiusSm
                    color: Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.15)
                    border.color: Theme.danger

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        FaIcon {
                            icon: Icons.stop
                            size: 11
                            iconColor: Theme.danger
                        }
                        Text {
                            text: "Stop"
                            color: Theme.danger
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Bridge.cancelBatchDownload()
                    }
                }

                // Close Button (when not downloading)
                Rectangle {
                    visible: !Bridge.isBatchDownloading
                    width: 90
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.surfaceElevated
                    border.color: Theme.border

                    Text {
                        anchors.centerIn: parent
                        text: "Close"
                        color: Theme.textSecondary
                        font.pixelSize: 11
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }

                // Start Download Button (when not downloading)
                Rectangle {
                    visible: !Bridge.isBatchDownloading
                    width: 170
                    height: 36
                    radius: Theme.radiusSm
                    opacity: root.selectedFolderPaths.length > 0 ? 1.0 : 0.4
                    color: (startMouse.containsMouse && root.selectedFolderPaths.length > 0) ? Theme.primaryHover : Theme.primary

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        FaIcon {
                            icon: Icons.download
                            size: 11
                            iconColor: "white"
                        }
                        Text {
                            text: root.selectedFolderPaths.length > 0 ? ("Start Download (" + root.selectedFolderPaths.length + ")") : "Start Download"
                            color: "white"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: startMouse
                        anchors.fill: parent
                        hoverEnabled: root.selectedFolderPaths.length > 0
                        cursorShape: root.selectedFolderPaths.length > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: {
                            var targets = root.selectedFolderPaths;
                            if (!targets || targets.length === 0) {
                                if (root.missingItemsList && root.missingItemsList.length > 0) {
                                    targets = [];
                                    for (var i = 0; i < root.missingItemsList.length; i++) {
                                        if (root.missingItemsList[i].folder_path) {
                                            targets.push(root.missingItemsList[i].folder_path);
                                        }
                                    }
                                }
                            }
                            if (targets && targets.length > 0) {
                                Bridge.retryMissingModelsList(targets);
                            } else if (root.selectedScope === "article" && root.selectedArticleFolder) {
                                Bridge.retryMissingModel(root.selectedArticleFolder);
                            }
                        }
                    }
                }
            }
        }
    }
}
