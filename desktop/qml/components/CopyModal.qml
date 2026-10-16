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
    property bool includeClientAgent: true
    property var selectedDrivePaths: []

    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

    onSelectedCategoryChanged: {
        if (copyCatCombo.model && copyCatCombo.model.length > 0) {
            var idx = copyCatCombo.model.indexOf(root.selectedCategory);
            if (idx >= 0) copyCatCombo.currentIndex = idx;
        }
    }

    onSelectedSubcategoryChanged: {
        if (copySubCombo.model && copySubCombo.model.length > 0) {
            var idx = copySubCombo.model.indexOf(root.selectedSubcategory);
            if (idx >= 0) copySubCombo.currentIndex = idx;
        }
    }

    function isDriveSelected(path) {
        if (!path || !root.selectedDrivePaths) return false;
        return root.selectedDrivePaths.indexOf(path) !== -1;
    }

    function toggleDrive(path) {
        if (!path) return;
        var list = (root.selectedDrivePaths || []).slice();
        var idx = list.indexOf(path);
        if (idx >= 0) {
            list.splice(idx, 1);
        } else {
            list.push(path);
        }
        root.selectedDrivePaths = list;
    }

    function syncDrivesList() {
        var flash = Bridge.flashDrives || [];
        var custom = Bridge.copyDestinations || [];
        var current = (root.selectedDrivePaths || []).slice();

        if (current.length === 0) {
            var allDrives = [];
            for (var i = 0; i < flash.length; i++) {
                if (flash[i] && flash[i].path && allDrives.indexOf(flash[i].path) === -1) {
                    allDrives.push(flash[i].path);
                }
            }
            for (var j = 0; j < custom.length; j++) {
                if (custom[j] && allDrives.indexOf(custom[j]) === -1) {
                    allDrives.push(custom[j]);
                }
            }
            root.selectedDrivePaths = allDrives;
        } else {
            var valid = {};
            for (var f = 0; f < flash.length; f++) {
                if (flash[f] && flash[f].path) valid[flash[f].path] = true;
            }
            for (var c = 0; c < custom.length; c++) {
                if (custom[c]) valid[custom[c]] = true;
            }
            var kept = [];
            for (var k = 0; k < current.length; k++) {
                if (valid[current[k]]) {
                    kept.push(current[k]);
                }
            }
            if (kept.length === 0 && flash.length > 0) {
                for (var m = 0; m < flash.length; m++) {
                    if (flash[m] && flash[m].path) kept.push(flash[m].path);
                }
            }
            root.selectedDrivePaths = kept;
        }
    }

    Connections {
        target: Bridge
        function onFlashDrivesChanged() {
            if (root.opacity > 0) {
                root.syncDrivesList();
            }
        }
        function onCopyDestinationsChanged() {
            if (root.opacity > 0) {
                root.syncDrivesList();
            }
        }
    }

    function open(scope, cat, sub, articleFolder, articleTitle) {
        if (scope) root.selectedScope = scope;
        if (cat) root.selectedCategory = cat;
        if (sub) root.selectedSubcategory = sub;
        if (articleFolder) root.selectedArticleFolder = articleFolder;
        if (articleTitle) root.selectedArticleTitle = articleTitle;

        Bridge.refreshFlashDrives();
        root.syncDrivesList();

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

        opacity = 1
        root.forceActiveFocus()
    }

    function close() {
        if (Bridge.isCopying) {
            Bridge.cancelCopy()
        }
        opacity = 0
    }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            if (!Bridge.isCopying) {
                root.close()
            }
        }
    }

    Keys.onEscapePressed: {
        if (!Bridge.isCopying) {
            root.close()
        }
    }

    Rectangle {
        id: card
        width: Math.min(parent.width - 40, 620)
        implicitHeight: cardCol.implicitHeight + 40
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
                        icon: Icons.copy
                        size: 16
                        iconColor: Theme.primaryLight
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: "Multi-Destination Disk Copy"
                        color: Theme.textPrimary
                        font.pixelSize: 15
                        font.bold: true
                    }
                    Text {
                        text: "Copy 3D models and client agent across multiple disks / USB drives simultaneously"
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

            // Scope Selector
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: !Bridge.isCopying

                Text {
                    text: "COPY SCOPE"
                    color: Theme.textMuted
                    font.pixelSize: 10
                    font.bold: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    // Article Pill (if selected)
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

                    // All Library
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
                                text: "All Articles"
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
                }

                // Scope dropdowns
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    visible: root.selectedScope === "category" || root.selectedScope === "subcategory"

                    ComboBox {
                        id: copyCatCombo
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
                            border.color: copyCatCombo.activeFocus ? Theme.primary : Theme.border
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
                                text: copyCatCombo.currentText || root.selectedCategory || "Select Category"
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
                            y: copyCatCombo.height + 4
                            width: copyCatCombo.width
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
                                model: copyCatCombo.popup.visible ? copyCatCombo.delegateModel : null
                                currentIndex: copyCatCombo.highlightedIndex
                                ScrollIndicator.vertical: ScrollIndicator {}
                            }
                        }

                        delegate: ItemDelegate {
                            width: copyCatCombo.width - 12
                            height: 34
                            highlighted: copyCatCombo.highlightedIndex === index

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
                        id: copySubCombo
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
                            border.color: copySubCombo.activeFocus ? Theme.primary : Theme.border
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
                                text: copySubCombo.currentText || root.selectedSubcategory || "Select Subcategory"
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
                            y: copySubCombo.height + 4
                            width: copySubCombo.width
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
                                model: copySubCombo.popup.visible ? copySubCombo.delegateModel : null
                                currentIndex: copySubCombo.highlightedIndex
                                ScrollIndicator.vertical: ScrollIndicator {}
                            }
                        }

                        delegate: ItemDelegate {
                            width: copySubCombo.width - 12
                            height: 34
                            highlighted: copySubCombo.highlightedIndex === index

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

                // Article title preview
                Rectangle {
                    visible: root.selectedScope === "article"
                    Layout.fillWidth: true
                    height: 36
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

            // Destination Disks Section
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        text: "TARGET FLASH DRIVES & DESTINATIONS (" + root.selectedDrivePaths.length + " SELECTED)"
                        color: Theme.textMuted
                        font.pixelSize: 10
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }

                    // Refresh / Scan Drives Button
                    Rectangle {
                        width: 106
                        height: 28
                        radius: Theme.radiusSm
                        color: scanDrivesMouse.containsMouse ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.25) : Theme.surfaceElevated
                        border.color: Theme.border
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 5
                            FaIcon {
                                icon: Icons.sync
                                size: 10
                                iconColor: Theme.primaryLight
                            }
                            Text {
                                text: "Scan Drives"
                                color: Theme.textPrimary
                                font.pixelSize: 10
                                font.bold: true
                            }
                        }

                        MouseArea {
                            id: scanDrivesMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            enabled: !Bridge.isCopying
                            onClicked: {
                                Bridge.refreshFlashDrives();
                                root.syncDrivesList();
                            }
                        }
                    }

                    // Add Destination Folder Button
                    Rectangle {
                        width: 110
                        height: 28
                        radius: Theme.radiusSm
                        color: addDiskMouse.containsMouse ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.25) : Theme.surfaceElevated
                        border.color: Theme.primary
                        border.width: 1

                        RowLayout {
                            anchors.centerIn: parent
                            spacing: 5
                            FaIcon {
                                icon: Icons.plus
                                size: 10
                                iconColor: Theme.primaryLight
                            }
                            Text {
                                text: "+ Add Folder"
                                color: Theme.primaryLight
                                font.pixelSize: 10
                                font.bold: true
                            }
                        }

                        MouseArea {
                            id: addDiskMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            enabled: !Bridge.isCopying
                            onClicked: Bridge.addCopyDestination()
                        }
                    }
                }

                // Disks List Box
                Rectangle {
                    Layout.fillWidth: true
                    height: 150
                    radius: Theme.radiusSm
                    color: Theme.card
                    border.color: Theme.border
                    clip: true

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 6
                        contentWidth: availableWidth
                        clip: true

                        ColumnLayout {
                            width: parent.width
                            spacing: 6

                            // Flash Drives Section
                            Text {
                                visible: Bridge.flashDrives && Bridge.flashDrives.length > 0
                                text: "DETECTED FLASH DRIVES / USB STICKS (" + (Bridge.flashDrives ? Bridge.flashDrives.length : 0) + ")"
                                color: Theme.primaryLight
                                font.pixelSize: 9
                                font.bold: true
                            }

                            Repeater {
                                model: Bridge.flashDrives
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    height: 38
                                    radius: 4
                                    color: root.isDriveSelected(modelData.path) ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.12) : Theme.surfaceElevated
                                    border.color: root.isDriveSelected(modelData.path) ? Theme.primary : Theme.border
                                    border.width: 1

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 8
                                        spacing: 8

                                        Rectangle {
                                            width: 16
                                            height: 16
                                            radius: 3
                                            color: root.isDriveSelected(modelData.path) ? Theme.primary : "transparent"
                                            border.color: root.isDriveSelected(modelData.path) ? Theme.primary : Theme.textMuted
                                            border.width: 1

                                            FaIcon {
                                                anchors.centerIn: parent
                                                icon: Icons.check
                                                size: 9
                                                iconColor: "white"
                                                visible: root.isDriveSelected(modelData.path)
                                            }
                                        }

                                        FaIcon {
                                            icon: Icons.hdd
                                            size: 13
                                            iconColor: root.isDriveSelected(modelData.path) ? Theme.primaryLight : Theme.textMuted
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 1

                                            Text {
                                                text: modelData.name || "Removable Drive"
                                                color: Theme.textPrimary
                                                font.pixelSize: 11
                                                font.bold: true
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                text: modelData.path
                                                color: Theme.textMuted
                                                font.pixelSize: 9
                                                elide: Text.ElideMiddle
                                            }
                                        }

                                        Rectangle {
                                            height: 20
                                            radius: 3
                                            color: Qt.rgba(Theme.surface.r, Theme.surface.g, Theme.surface.b, 0.9)
                                            border.color: Theme.border
                                            implicitWidth: driveSpaceTxt.implicitWidth + 12

                                            Text {
                                                id: driveSpaceTxt
                                                anchors.centerIn: parent
                                                text: (modelData.free_text || "") + " free / " + (modelData.total_text || "")
                                                color: Theme.textSecondary
                                                font.pixelSize: 9
                                                font.bold: true
                                            }
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        enabled: !Bridge.isCopying
                                        onClicked: root.toggleDrive(modelData.path)
                                    }
                                }
                            }

                            // Custom Destinations Section
                            Text {
                                visible: Bridge.copyDestinations && Bridge.copyDestinations.length > 0
                                text: "CUSTOM FOLDERS / DISKS (" + (Bridge.copyDestinations ? Bridge.copyDestinations.length : 0) + ")"
                                color: Theme.textMuted
                                font.pixelSize: 9
                                font.bold: true
                            }

                            Repeater {
                                model: Bridge.copyDestinations
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    height: 34
                                    radius: 4
                                    color: root.isDriveSelected(modelData) ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.12) : Theme.surfaceElevated
                                    border.color: root.isDriveSelected(modelData) ? Theme.primary : Theme.border
                                    border.width: 1

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 8
                                        anchors.rightMargin: 8
                                        spacing: 8

                                        Rectangle {
                                            width: 16
                                            height: 16
                                            radius: 3
                                            color: root.isDriveSelected(modelData) ? Theme.primary : "transparent"
                                            border.color: root.isDriveSelected(modelData) ? Theme.primary : Theme.textMuted
                                            border.width: 1

                                            FaIcon {
                                                anchors.centerIn: parent
                                                icon: Icons.check
                                                size: 9
                                                iconColor: "white"
                                                visible: root.isDriveSelected(modelData)
                                            }
                                        }

                                        FaIcon {
                                            icon: Icons.folder
                                            size: 12
                                            iconColor: Theme.primaryLight
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData
                                            color: Theme.textPrimary
                                            font.pixelSize: 11
                                            elide: Text.ElideMiddle
                                        }

                                        FaIcon {
                                            icon: Icons.times
                                            size: 11
                                            iconColor: Theme.danger
                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                enabled: !Bridge.isCopying
                                                onClicked: {
                                                    Bridge.removeCopyDestination(modelData);
                                                    var list = (root.selectedDrivePaths || []).slice();
                                                    var idx = list.indexOf(modelData);
                                                    if (idx >= 0) {
                                                        list.splice(idx, 1);
                                                        root.selectedDrivePaths = list;
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        anchors.rightMargin: 26
                                        cursorShape: Qt.PointingHandCursor
                                        enabled: !Bridge.isCopying
                                        onClicked: root.toggleDrive(modelData)
                                    }
                                }
                            }

                            // Empty state when no flash drives and no custom destinations
                            Rectangle {
                                visible: (!Bridge.flashDrives || Bridge.flashDrives.length === 0) && (!Bridge.copyDestinations || Bridge.copyDestinations.length === 0)
                                Layout.fillWidth: true
                                height: 50
                                color: "transparent"

                                RowLayout {
                                    anchors.centerIn: parent
                                    spacing: 8

                                    FaIcon {
                                        icon: Icons.infoCircle
                                        size: 13
                                        iconColor: Theme.warning
                                    }

                                    Text {
                                        text: "No flash drives detected. Plug in your USB drive & click 'Scan Drives', or click '+ Add Folder'."
                                        color: Theme.warning
                                        font.pixelSize: 10
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Client Agent Integration Card
            Rectangle {
                Layout.fillWidth: true
                height: 48
                radius: Theme.radiusSm
                color: Theme.surfaceElevated
                border.color: Bridge.clientAgentPath ? Qt.rgba(Theme.success.r, Theme.success.g, Theme.success.b, 0.4) : Theme.border
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10

                    FaIcon {
                        icon: Bridge.clientAgentPath ? Icons.checkCircle : Icons.infoCircle
                        size: 14
                        iconColor: Bridge.clientAgentPath ? Theme.success : Theme.warning
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text {
                            text: Bridge.clientAgentPath ? ("Client Agent: " + Bridge.clientAgentPath.split("/").pop().split("\\").pop()) : "Client Agent: Not Configured"
                            color: Bridge.clientAgentPath ? Theme.textPrimary : Theme.textMuted
                            font.pixelSize: 11
                            font.bold: true
                            elide: Text.ElideMiddle
                        }
                        Text {
                            text: Bridge.clientAgentPath ? "Will be auto-copied to every destination disk root alongside articles" : "Select an .exe file in Settings to auto-copy with articles"
                            color: Theme.textMuted
                            font.pixelSize: 9
                        }
                    }

                    CheckBox {
                        id: agentCheck
                        text: "Include"
                        checked: root.includeClientAgent
                        enabled: !Bridge.isCopying && !!Bridge.clientAgentPath
                        onCheckedChanged: root.includeClientAgent = checked
                    }
                }
            }

            // Copy Progress & Status
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                visible: Bridge.isCopying

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "COPY PROGRESS"
                        color: Theme.textMuted
                        font.pixelSize: 10
                        font.bold: true
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: (Bridge.copyProgress.bytesText || "0 B") + " (" + Math.round(Bridge.copyProgress.percent || 0) + "%)"
                        color: Theme.primaryLight
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 8
                    radius: 4
                    color: Theme.surfaceElevated
                    clip: true

                    Rectangle {
                        height: parent.height
                        width: parent.width * Math.min(Math.max((Bridge.copyProgress.percent || 0) / 100.0, 0.0), 1.0)
                        radius: 4
                        color: Theme.primary
                        Behavior on width { NumberAnimation { duration: 250 } }
                    }
                }

                Text {
                    text: (Bridge.copyProgress.title || "") + " • " + (Bridge.copyProgress.currentDest || "")
                    color: Theme.textSecondary
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }

            // Footer Actions
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Item { Layout.fillWidth: true }

                Rectangle {
                    visible: Bridge.isCopying
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
                        onClicked: Bridge.cancelCopy()
                    }
                }

                Rectangle {
                    visible: !Bridge.isCopying
                    width: 90
                    height: 36
                    radius: Theme.radiusSm
                    color: Theme.surfaceElevated
                    border.color: Theme.border

                    Text {
                        anchors.centerIn: parent
                        text: "Cancel"
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

                Rectangle {
                    visible: !Bridge.isCopying
                    width: 200
                    height: 36
                    radius: Theme.radiusSm
                    color: root.selectedDrivePaths.length > 0 ? (startCopyMouse.containsMouse ? Theme.primaryHover : Theme.primary) : Theme.card
                    border.color: root.selectedDrivePaths.length > 0 ? Theme.primary : Theme.border
                    opacity: root.selectedDrivePaths.length > 0 ? 1.0 : 0.5

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 6
                        FaIcon {
                            icon: Icons.copy
                            size: 11
                            iconColor: "white"
                        }
                        Text {
                            text: "Start Copy to " + root.selectedDrivePaths.length + " Drive(s)"
                            color: "white"
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: startCopyMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: root.selectedDrivePaths.length > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                        enabled: root.selectedDrivePaths.length > 0
                        onClicked: {
                            var targetParam = null;
                            if (root.selectedScope === "article") {
                                targetParam = root.selectedArticleFolder;
                            } else if (root.selectedScope === "category") {
                                targetParam = root.selectedCategory;
                            } else if (root.selectedScope === "subcategory") {
                                targetParam = { "category": root.selectedCategory, "subcategory": root.selectedSubcategory };
                            }
                            Bridge.startCopy(root.selectedScope, targetParam, root.selectedDrivePaths, root.includeClientAgent);
                        }
                    }
                }
            }
        }
    }
}
