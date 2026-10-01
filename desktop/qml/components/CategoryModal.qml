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

    property string selectedCategory: ""
    property string selectedSubcategory: ""
    property string selectedFeedUrl: ""
    property var expandedCategories: ({})
    property string categoryFilter: ""

    signal subcategorySelected(string categoryTitle, string subcategoryTitle, string feedUrl)

    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

    function open() {
        opacity = 1
        catFilterInput.text = ""
        root.categoryFilter = ""
        root.forceActiveFocus()
        if (root.selectedCategory) {
            var exp = Object.assign({}, root.expandedCategories);
            exp[root.selectedCategory] = true;
            root.expandedCategories = exp;
        }
        if (Bridge.categories.length === 0) {
            Bridge.loadCategories(false)
        }
    }

    function close() {
        opacity = 0
    }

    function toggleCategory(catTitle) {
        var exp = Object.assign({}, root.expandedCategories);
        exp[catTitle] = !exp[catTitle];
        root.expandedCategories = exp;
    }

    // Dismiss on clicking backdrop
    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    // Escape key closes modal
    Keys.onEscapePressed: root.close()

    // Dialog Modal Container
    Rectangle {
        id: dialogCard
        width: Math.min(parent.width - 40, 480)
        height: Math.min(parent.height - 60, 640)
        anchors.centerIn: parent
        radius: Theme.radiusLg
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        clip: true

        scale: root.opacity > 0 ? 1.0 : 0.95
        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

        // Block clicks through dialog
        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 14

            // Modal Header
            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Rectangle {
                    width: 34
                    height: 34
                    radius: Theme.radiusSm
                    color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.15)
                    FaIcon {
                        anchors.centerIn: parent
                        icon: Icons.layerGroup
                        size: 14
                        iconColor: Theme.primaryLight
                    }
                }

                ColumnLayout {
                    spacing: 2
                    Text {
                        text: "Categories Tree"
                        color: Theme.textPrimary
                        font.pixelSize: 14
                        font.bold: true
                    }
                    Text {
                        text: Bridge.categories.length + " taxonomy groups • Select to browse live feed"
                        color: Theme.textMuted
                        font.pixelSize: 11
                    }
                }

                Item { Layout.fillWidth: true }

                // Refresh Button
                Rectangle {
                    width: 78
                    height: 30
                    radius: Theme.radiusSm
                    color: refreshMouse.containsMouse ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.2) : Theme.surfaceElevated
                    border.color: Theme.border

                    RowLayout {
                        anchors.centerIn: parent
                        spacing: 5
                        FaIcon {
                            icon: Icons.rotate
                            size: 10
                            iconColor: Bridge.categoriesLoading ? Theme.primaryLight : Theme.textSecondary
                            RotationAnimation on rotation {
                                running: Bridge.categoriesLoading
                                loops: Animation.Infinite
                                from: 0
                                to: 360
                                duration: 1000
                            }
                        }
                        Text {
                            text: Bridge.categoriesLoading ? "Loading" : "Refresh"
                            color: Theme.textSecondary
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    MouseArea {
                        id: refreshMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        enabled: !Bridge.categoriesLoading
                        onClicked: Bridge.loadCategories(true)
                    }
                }

                // Close Button
                Rectangle {
                    width: 30
                    height: 30
                    radius: Theme.radiusSm
                    color: closeMouse.containsMouse ? Qt.rgba(Theme.error.r, Theme.error.g, Theme.error.b, 0.2) : Theme.surfaceElevated
                    border.color: Theme.border

                    FaIcon {
                        anchors.centerIn: parent
                        icon: Icons.times
                        size: 11
                        iconColor: closeMouse.containsMouse ? Theme.error : Theme.textSecondary
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

            // Filter Search Input
            Rectangle {
                Layout.fillWidth: true
                height: 36
                radius: Theme.radiusSm
                color: Theme.surfaceElevated
                border.color: catFilterInput.activeFocus ? Theme.primary : Theme.border
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8

                    FaIcon {
                        icon: Icons.search
                        size: 11
                        iconColor: Theme.textMuted
                    }

                    TextInput {
                        id: catFilterInput
                        Layout.fillWidth: true
                        color: Theme.textPrimary
                        font.pixelSize: 11
                        selectByMouse: true
                        clip: true

                        Text {
                            text: "Filter categories & feeds..."
                            color: Theme.textMuted
                            font.pixelSize: 11
                            visible: !catFilterInput.text && !catFilterInput.activeFocus
                        }

                        onTextChanged: root.categoryFilter = text.trim().toLowerCase()
                    }

                    FaIcon {
                        icon: Icons.times
                        size: 10
                        iconColor: Theme.textMuted
                        visible: catFilterInput.text.length > 0
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: catFilterInput.text = ""
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.border
            }

            // Categories Tree ListView
            ListView {
                id: catList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 6
                model: Bridge.categories

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AsNeeded
                }

                delegate: ColumnLayout {
                    id: catItem
                    width: catList.width - (catList.ScrollBar.vertical.visible ? 10 : 0)
                    spacing: 4

                    property var catData: modelData
                    property bool isExpanded: !!root.expandedCategories[modelData.title] || root.categoryFilter.length > 0
                    property int subsCount: (modelData.subcategories ? modelData.subcategories.length : 0)

                    // Category Header Card
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 38
                        Layout.preferredHeight: 38
                        radius: Theme.radiusSm
                        color: catHeaderMouse.containsMouse 
                            ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.18) 
                            : (catItem.isExpanded ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.10) : Theme.card)
                        border.color: catItem.isExpanded ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.35) : Theme.border
                        border.width: 1

                        Behavior on color { ColorAnimation { duration: 150 } }
                        Behavior on border.color { ColorAnimation { duration: 150 } }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            FaIcon {
                                icon: catItem.isExpanded ? Icons.chevronDown : Icons.chevronRight
                                size: 9
                                iconColor: catItem.isExpanded ? Theme.primaryLight : Theme.textMuted
                            }

                            FaIcon {
                                icon: catItem.isExpanded ? Icons.folderOpen : Icons.folder
                                size: 13
                                iconColor: catItem.isExpanded ? Theme.primaryLight : Theme.textSecondary
                            }

                            Text {
                                text: modelData.title || "Category"
                                color: catItem.isExpanded ? Theme.textPrimary : Theme.textSecondary
                                font.pixelSize: 12
                                font.bold: true
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }

                            // Subcategories count badge
                            Rectangle {
                                width: countText.width + 12
                                height: 18
                                radius: 9
                                color: Theme.surfaceElevated
                                border.color: Theme.border

                                Text {
                                    id: countText
                                    anchors.centerIn: parent
                                    text: catItem.subsCount.toString()
                                    color: Theme.textMuted
                                    font.pixelSize: 9
                                    font.bold: true
                                }
                            }
                        }

                        MouseArea {
                            id: catHeaderMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.toggleCategory(modelData.title)
                        }
                    }

                    // Subcategories Nested List
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: catItem.isExpanded
                        spacing: 3

                        Repeater {
                            model: modelData.subcategories || []

                            delegate: Rectangle {
                                id: subRow
                                property bool isMatchesFilter: !root.categoryFilter 
                                    || modelData.title.toLowerCase().indexOf(root.categoryFilter) !== -1 
                                    || catItem.catData.title.toLowerCase().indexOf(root.categoryFilter) !== -1
                                visible: isMatchesFilter
                                Layout.fillWidth: true
                                Layout.leftMargin: 18
                                implicitHeight: visible ? 32 : 0
                                Layout.preferredHeight: visible ? 32 : 0
                                radius: Theme.radiusSm
                                clip: true

                                property bool isSelected: (root.selectedSubcategory === modelData.title && root.selectedCategory === catItem.catData.title)
                                color: isSelected 
                                    ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.22) 
                                    : (subMouse.containsMouse ? Theme.surfaceElevated : "transparent")
                                border.color: isSelected ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.5) : "transparent"
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 12
                                    spacing: 8

                                    FaIcon {
                                        icon: Icons.rss
                                        size: 9
                                        iconColor: subRow.isSelected ? "#F59E0B" : Theme.textMuted
                                    }

                                    Text {
                                        text: modelData.title
                                        color: subRow.isSelected ? Theme.textPrimary : (subMouse.containsMouse ? Theme.textPrimary : Theme.textSecondary)
                                        font.pixelSize: 11
                                        font.weight: subRow.isSelected ? Font.Bold : Font.Normal
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }

                                    FaIcon {
                                        visible: subRow.isSelected
                                        icon: Icons.chevronRight
                                        size: 8
                                        iconColor: Theme.primaryLight
                                    }
                                }

                                MouseArea {
                                    id: subMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        root.selectedCategory = catItem.catData.title
                                        root.selectedSubcategory = modelData.title
                                        root.selectedFeedUrl = modelData.feed_url
                                        root.subcategorySelected(catItem.catData.title, modelData.title, modelData.feed_url)
                                        root.close()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
