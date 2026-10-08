import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "."

// Picks several categories / sub-categories and queues them as one bulk download.
Rectangle {
    id: root
    anchors.fill: parent
    color: "#D9050811"
    z: 9999
    visible: opacity > 0
    opacity: 0

    // Passed in from the Categories view's toolbar.
    property int limitValue: 0
    property bool wantModels: true
    property bool wantImages: true

    property var picked: ({})            // "<category>␟<sub>" -> {category, subcategory, feed_url}
    property int pickedCount: 0
    property var expanded: ({})

    Behavior on opacity { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

    function open() {
        opacity = 1
        root.forceActiveFocus()
        if (Bridge.categories.length === 0)
            Bridge.loadCategories(false)
    }
    function close() { opacity = 0 }

    function key(cat, sub) { return cat + "␟" + sub }
    function isPicked(cat, sub) { return root.picked[key(cat, sub)] !== undefined }

    function pickedIn(cat) {
        var n = 0
        for (var i = 0; i < cat.subcategories.length; ++i)
            if (isPicked(cat.title, cat.subcategories[i].title)) n++
        return n
    }

    function commit(next) {
        root.picked = next
        root.pickedCount = Object.keys(next).length
    }

    function toggleSub(cat, sub) {
        var next = Object.assign({}, root.picked)
        var k = key(cat.title, sub.title)
        if (next[k] !== undefined) delete next[k]
        else next[k] = { category: cat.title, subcategory: sub.title, feed_url: sub.feed_url }
        commit(next)
    }

    function toggleCategory(cat) {
        var next = Object.assign({}, root.picked)
        var all = pickedIn(cat) === cat.subcategories.length
        for (var i = 0; i < cat.subcategories.length; ++i) {
            var sub = cat.subcategories[i]
            var k = key(cat.title, sub.title)
            if (all) delete next[k]
            else next[k] = { category: cat.title, subcategory: sub.title, feed_url: sub.feed_url }
        }
        commit(next)
    }

    function selectAll() {
        var next = {}
        for (var i = 0; i < Bridge.categories.length; ++i) {
            var cat = Bridge.categories[i]
            for (var j = 0; j < cat.subcategories.length; ++j) {
                var sub = cat.subcategories[j]
                next[key(cat.title, sub.title)] = { category: cat.title, subcategory: sub.title, feed_url: sub.feed_url }
            }
        }
        commit(next)
    }

    function toggleExpanded(title) {
        var e = Object.assign({}, root.expanded)
        e[title] = !e[title]
        root.expanded = e
    }

    function start() {
        // Keep the category tree's order so downloads run category by category.
        var groups = []
        for (var i = 0; i < Bridge.categories.length; ++i) {
            var cat = Bridge.categories[i]
            for (var j = 0; j < cat.subcategories.length; ++j) {
                var g = root.picked[key(cat.title, cat.subcategories[j].title)]
                if (g) groups.push(g)
            }
        }
        Bridge.startBulkSubcategories(groups, root.limitValue, root.wantModels, root.wantImages)
        close()
    }

    MouseArea { anchors.fill: parent; onClicked: root.close() }
    Keys.onEscapePressed: root.close()

    Rectangle {
        id: card
        width: Math.min(parent.width - 40, 520)
        height: Math.min(parent.height - 60, 680)
        anchors.centerIn: parent
        radius: Theme.radiusLg
        color: Theme.surface
        border.color: Theme.border
        border.width: 1
        clip: true
        scale: root.opacity > 0 ? 1.0 : 0.95
        Behavior on scale { NumberAnimation { duration: 180; easing.type: Easing.OutQuad } }

        MouseArea { anchors.fill: parent; onClicked: {} }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Rectangle {
                    width: 34; height: 34
                    radius: Theme.radiusSm
                    color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.15)
                    FaIcon { anchors.centerIn: parent; icon: Icons.cubes; size: 14; iconColor: Theme.primaryLight }
                }
                ColumnLayout {
                    spacing: 2
                    Layout.fillWidth: true
                    Text { text: "Bulk download categories"; color: Theme.textPrimary; font.pixelSize: 14; font.bold: true }
                    Text {
                        text: "Tick categories or single sub-categories; their articles are added to the download queue."
                        color: Theme.textMuted; font.pixelSize: 10
                        Layout.fillWidth: true; wrapMode: Text.Wrap
                    }
                }
                Rectangle {
                    width: 30; height: 30
                    radius: Theme.radiusSm
                    color: closeMouse.containsMouse ? Theme.surfaceElevated : "transparent"
                    FaIcon { anchors.centerIn: parent; icon: Icons.times; size: 12; iconColor: Theme.textSecondary }
                    MouseArea { id: closeMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.close() }
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8
                ActionButton { text: "Select all"; icon: Icons.squareCheck; onClicked: root.selectAll() }
                ActionButton { text: "Clear"; icon: Icons.times; enabled: root.pickedCount > 0; onClicked: root.commit({}) }
            }

            ListView {
                id: catList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 4
                model: Bridge.categories
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                delegate: Column {
                    id: catDelegate
                    width: catList.width - 10
                    readonly property var cat: modelData
                    readonly property int nPicked: { root.picked; return root.pickedIn(modelData) }
                    readonly property bool open: !!root.expanded[modelData.title]

                    Rectangle {
                        width: parent.width
                        height: 40
                        radius: Theme.radiusMd
                        color: catMouse.containsMouse ? Theme.surfaceElevated : Theme.card
                        border.color: catDelegate.nPicked > 0 ? Theme.primary : Theme.border
                        border.width: 1

                        MouseArea { id: catMouse; anchors.fill: parent; hoverEnabled: true; onClicked: root.toggleExpanded(catDelegate.cat.title) }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 10

                            // Category checkbox: all / some / none of its sub-categories
                            Rectangle {
                                width: 20; height: 20; radius: 4
                                color: catDelegate.nPicked > 0 ? Theme.primary : "#0F172A"
                                border.color: catDelegate.nPicked > 0 ? Theme.primaryLight : "#334155"
                                FaIcon {
                                    anchors.centerIn: parent
                                    visible: catDelegate.nPicked === catDelegate.cat.subcategories.length && catDelegate.nPicked > 0
                                    icon: Icons.check; size: 10; iconColor: "white"
                                }
                                Rectangle {
                                    anchors.centerIn: parent
                                    visible: catDelegate.nPicked > 0 && catDelegate.nPicked < catDelegate.cat.subcategories.length
                                    width: 10; height: 2; color: "white"
                                }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.toggleCategory(catDelegate.cat) }
                            }
                            Text {
                                text: catDelegate.cat.title
                                color: Theme.textPrimary; font.pixelSize: 12; font.bold: true
                                Layout.fillWidth: true; elide: Text.ElideRight
                            }
                            Text {
                                text: catDelegate.nPicked + " / " + catDelegate.cat.subcategories.length
                                color: catDelegate.nPicked > 0 ? Theme.primaryLight : Theme.textMuted
                                font.pixelSize: 10; font.bold: true
                            }
                            FaIcon {
                                icon: catDelegate.open ? Icons.chevronDown : Icons.chevronRight
                                size: 10; iconColor: Theme.textSecondary
                            }
                        }
                    }

                    Repeater {
                        model: catDelegate.open ? catDelegate.cat.subcategories : []
                        delegate: Rectangle {
                            id: subRow
                            readonly property bool on: { root.picked; return root.isPicked(catDelegate.cat.title, modelData.title) }
                            x: 28
                            width: catDelegate.width - 28
                            height: 32
                            color: subMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.04) : "transparent"
                            radius: Theme.radiusSm
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                spacing: 10
                                Rectangle {
                                    width: 16; height: 16; radius: 3
                                    color: subRow.on ? Theme.primary : "#0F172A"
                                    border.color: subRow.on ? Theme.primaryLight : "#334155"
                                    FaIcon { anchors.centerIn: parent; visible: subRow.on; icon: Icons.check; size: 8; iconColor: "white" }
                                }
                                Text {
                                    text: modelData.title
                                    color: Theme.textSecondary; font.pixelSize: 11
                                    Layout.fillWidth: true; elide: Text.ElideRight
                                }
                            }
                            MouseArea {
                                id: subMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.toggleSub(catDelegate.cat, modelData)
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10
                Text {
                    text: "Per feed: " + (root.limitValue === 0 ? "all articles" : root.limitValue)
                          + "  •  " + (root.wantModels ? "models" : "") + (root.wantModels && root.wantImages ? " + " : "")
                          + (root.wantImages ? "images" : "")
                    color: Theme.textMuted; font.pixelSize: 10
                    Layout.fillWidth: true; elide: Text.ElideRight
                }
                ActionButton {
                    text: root.pickedCount > 0 ? "Queue " + root.pickedCount + " sub-categories" : "Pick sub-categories"
                    icon: Icons.download
                    primary: true
                    enabled: root.pickedCount > 0
                    onClicked: root.start()
                }
            }
        }
    }
}
