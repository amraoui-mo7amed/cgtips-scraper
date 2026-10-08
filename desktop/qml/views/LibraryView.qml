import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "../components"

Item {
    id: root

    signal openGallery(var images, string title)
    signal openBatchDownloadRequested(string scope, string cat, string sub, string articleFolder, string articleTitle)
    signal openCopyRequested(string scope, string cat, string sub, string articleFolder, string articleTitle)
    signal openUploadRequested(string scope, string cat, string sub, string articleFolder, string articleTitle)
    signal openClearConfirmRequested()

    property string selectedCategory: "all"
    property bool isMissingOnly: false

    function reloadLibrary() {
        Bridge.loadLibrary(libFilterInput.text.trim(), root.selectedCategory, root.isMissingOnly);
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 16

        // Header & Action Bar
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

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

                        onTextChanged: root.reloadLibrary()
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
                                root.reloadLibrary()
                            }
                        }
                    }
                }
            }

            // Category filter dropdown
            ComboBox {
                id: libCatCombo
                Layout.preferredWidth: 150
                Layout.preferredHeight: 40
                model: ["All Categories"].concat(Bridge.categoryNames || [])
                indicator: Item {}
                leftPadding: 12
                rightPadding: 12

                currentIndex: {
                    if (!model || model.length === 0) return 0;
                    if (root.selectedCategory === "all") return 0;
                    var idx = model.indexOf(root.selectedCategory);
                    return idx >= 0 ? idx : 0;
                }

                onActivated: function(index) {
                    if (index === 0) {
                        root.selectedCategory = "all";
                    } else {
                        root.selectedCategory = model[index];
                    }
                    root.reloadLibrary();
                }

                background: Rectangle {
                    implicitHeight: 40
                    radius: Theme.radiusMd
                    color: Theme.surface
                    border.color: libCatCombo.activeFocus ? Theme.primary : Theme.border
                    border.width: 1
                }

                contentItem: RowLayout {
                    spacing: 6

                    FaIcon {
                        icon: Icons.layerGroup
                        size: 11
                        iconColor: root.selectedCategory !== "all" ? Theme.primaryLight : Theme.textMuted
                    }

                    Text {
                        Layout.fillWidth: true
                        text: libCatCombo.currentText || "All Categories"
                        color: root.selectedCategory !== "all" ? Theme.primaryLight : Theme.textPrimary
                        font.pixelSize: 11
                        font.bold: root.selectedCategory !== "all"
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    FaIcon {
                        icon: Icons.chevronDown
                        size: 8
                        iconColor: Theme.textMuted
                    }
                }

                popup: Popup {
                    y: libCatCombo.height + 4
                    width: libCatCombo.width
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
                        model: libCatCombo.popup.visible ? libCatCombo.delegateModel : null
                        currentIndex: libCatCombo.highlightedIndex
                        ScrollIndicator.vertical: ScrollIndicator {}
                    }
                }

                delegate: ItemDelegate {
                    width: libCatCombo.width - 12
                    height: 32
                    highlighted: libCatCombo.highlightedIndex === index

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

            // Missing Only Filter Toggle Pill
            Rectangle {
                width: missingFilterRow.implicitWidth + 20
                height: 40
                radius: Theme.radiusMd
                color: root.isMissingOnly ? Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.2) : Theme.surface
                border.color: root.isMissingOnly ? Theme.warning : Theme.border
                border.width: 1

                RowLayout {
                    id: missingFilterRow
                    anchors.centerIn: parent
                    spacing: 6
                    FaIcon {
                        icon: Icons.exclamationTriangle
                        size: 11
                        iconColor: root.isMissingOnly ? Theme.warning : Theme.textMuted
                    }
                    Text {
                        text: root.isMissingOnly ? "Missing Only" : "Show Missing"
                        color: root.isMissingOnly ? Theme.warning : Theme.textSecondary
                        font.pixelSize: 11
                        font.bold: root.isMissingOnly
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.isMissingOnly = !root.isMissingOnly;
                        root.reloadLibrary();
                    }
                }
            }

            // Stats info pill
            Rectangle {
                width: 110
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

            // Missing models pill & re-download button (if missing > 0)
            Rectangle {
                visible: Bridge.missingModelsCount > 0
                width: missingRow.implicitWidth + 24
                height: 40
                radius: Theme.radiusMd
                color: missingBtnMouse.containsMouse ? Theme.warning : Qt.rgba(Theme.warning.r, Theme.warning.g, Theme.warning.b, 0.2)
                border.color: Theme.warning
                border.width: 1

                RowLayout {
                    id: missingRow
                    anchors.centerIn: parent
                    spacing: 7
                    FaIcon {
                        icon: Icons.download
                        size: 12
                        iconColor: missingBtnMouse.containsMouse ? "white" : Theme.warning
                    }
                    Text {
                        text: root.selectedCategory !== "all" ? ("Re-Download in " + root.selectedCategory) : ("Re-Download Missing (" + Bridge.missingModelsCount + ")")
                        color: missingBtnMouse.containsMouse ? "white" : Theme.warning
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                MouseArea {
                    id: missingBtnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.selectedCategory !== "all") {
                            root.openBatchDownloadRequested("category", root.selectedCategory, "", "", "");
                        } else {
                            root.openBatchDownloadRequested("all", "", "", "", "");
                        }
                    }
                }
            }

            // Copy Articles Button
            Rectangle {
                width: 125
                height: 40
                radius: Theme.radiusMd
                color: copyBtnMouse.containsMouse ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.25) : Theme.surface
                border.color: copyBtnMouse.containsMouse ? Theme.primary : Theme.border
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 6
                    FaIcon {
                        icon: Icons.copy
                        size: 12
                        iconColor: Theme.primaryLight
                    }
                    Text {
                        text: "Copy Articles"
                        color: Theme.primaryLight
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                MouseArea {
                    id: copyBtnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.openCopyRequested("all", "", "", "", "")
                }
            }

            // Upload to Loft Gallery Button
            Rectangle {
                width: 135
                height: 40
                radius: Theme.radiusMd
                color: uploadBtnMouse.containsMouse ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.25) : Theme.surface
                border.color: uploadBtnMouse.containsMouse ? Theme.primary : Theme.border
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 6
                    FaIcon {
                        icon: Icons.cloudUpload
                        size: 11
                        iconColor: Theme.primaryLight
                    }
                    Text {
                        text: "Upload to Loft"
                        color: Theme.primaryLight
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                MouseArea {
                    id: uploadBtnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.selectedCategory !== "all") {
                            root.openUploadRequested("category", root.selectedCategory, "", "", "");
                        } else {
                            root.openUploadRequested("all", "", "", "", "");
                        }
                    }
                }
            }

            // Clear Download List Button
            Rectangle {
                width: 135
                height: 40
                radius: Theme.radiusMd
                color: clearBtnMouse.containsMouse ? Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.2) : Theme.surface
                border.color: clearBtnMouse.containsMouse ? Theme.danger : Theme.border
                border.width: 1

                RowLayout {
                    anchors.centerIn: parent
                    spacing: 6
                    FaIcon {
                        icon: Icons.trash
                        size: 11
                        iconColor: clearBtnMouse.containsMouse ? Theme.danger : Theme.textSecondary
                    }
                    Text {
                        text: "Clear Download List"
                        color: clearBtnMouse.containsMouse ? Theme.danger : Theme.textSecondary
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                MouseArea {
                    id: clearBtnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.openClearConfirmRequested()
                }
            }

            // Open Folder in Finder Button
            Rectangle {
                width: 40
                height: 40
                radius: Theme.radiusMd
                color: openFinderMouse.containsMouse ? Theme.surfaceElevated : Theme.surface
                border.color: Theme.border

                FaIcon {
                    anchors.centerIn: parent
                    icon: Icons.folderOpen
                    size: 13
                    iconColor: Theme.primaryLight
                }

                MouseArea {
                    id: openFinderMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: Bridge.openFolder("")
                }
            }

            // Reload Button
            Rectangle {
                width: 40
                height: 40
                radius: Theme.radiusMd
                color: reloadMouse.containsMouse ? Theme.surfaceElevated : Theme.surface
                border.color: Theme.border

                FaIcon {
                    anchors.centerIn: parent
                    icon: Icons.rotate
                    size: 13
                    iconColor: Theme.textPrimary
                }

                MouseArea {
                    id: reloadMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.reloadLibrary()
                }
            }
        }

        // Library Items Grid / Empty State
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            BusyIndicator {
                anchors.centerIn: parent
                running: Bridge.libraryLoading
                visible: Bridge.libraryLoading
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
                    text: "Download List is Empty"
                    color: Theme.textPrimary
                    font.pixelSize: 15
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                }
                Text {
                    text: "You haven't downloaded any 3D models yet.\nUse Explore or Categories to download models."
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
                        onCopyRequested: function(data) {
                            root.openCopyRequested("article", data.category, data.subcategory, data.folder_path, data.title)
                        }
                        onUploadRequested: function(data) {
                            root.openUploadRequested("article", data.category, data.subcategory, data.folder_path, data.title)
                        }
                        onRetryRequested: function(data) {
                            root.openBatchDownloadRequested("article", data.category, data.subcategory, data.folder_path, data.title)
                        }
                    }
                }
            }
        }
    }
}
