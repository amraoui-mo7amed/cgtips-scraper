import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import "../components"
import ".."

// The download queue: everything waiting, downloading, finished or failed.
Item {
    id: root

    readonly property var st: Bridge.queueStats || ({})
    readonly property var prog: Bridge.queueProgress || ({})
    property string filter: "all"   // all | waiting | failed | done

    readonly property var shown: {
        var out = []
        var items = Bridge.queueItems || []
        for (var i = 0; i < items.length; ++i) {
            var s = items[i].status
            if (root.filter === "waiting" && !(s === "pending" || s === "paused" || s === "downloading")) continue
            if (root.filter === "failed" && s !== "failed") continue
            if (root.filter === "done" && !(s === "done" || s === "skipped")) continue
            out.push(items[i])
        }
        return out
    }

    function fmtBytes(b) {
        if (!b) return "0 B"
        var u = ["B", "KB", "MB", "GB"], i = 0
        while (b >= 1024 && i < u.length - 1) { b /= 1024; i++ }
        return b.toFixed(i >= 2 ? 1 : 0) + " " + u[i]
    }

    function statusColor(s) {
        switch (s) {
            case "downloading": return Theme.primaryLight
            case "paused": return Theme.warning
            case "done": return Theme.success
            case "skipped": return Theme.textSecondary
            case "failed": return Theme.error
            default: return Theme.textMuted
        }
    }
    function statusIcon(s) {
        switch (s) {
            case "downloading": return Icons.download
            case "paused": return Icons.pause
            case "done": return Icons.checkCircle
            case "skipped": return Icons.check
            case "failed": return Icons.exclamationTriangle
            default: return Icons.clock
        }
    }
    function statusText(it) {
        switch (it.status) {
            case "downloading": return "Downloading"
            case "paused": return it.bytes_done ? "Paused at " + fmtBytes(it.bytes_done) + (it.bytes_total ? " of " + fmtBytes(it.bytes_total) : "") : "Paused"
            case "done": return "Downloaded"
            case "skipped": return it.error || "Skipped"
            case "failed": return it.error || "Failed"
            default: return "Waiting"
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

        // Summary + controls
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: headCol.implicitHeight + 32
            radius: Theme.radiusLg
            color: Theme.surface
            border.color: Theme.border

            ColumnLayout {
                id: headCol
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 18
                    Repeater {
                        model: [
                            { label: "Waiting", value: (root.st.active || 0), color: Theme.primaryLight },
                            { label: "Downloaded", value: (root.st.done || 0), color: Theme.success },
                            { label: "Skipped", value: (root.st.skipped || 0), color: Theme.textSecondary },
                            { label: "Failed", value: (root.st.failed || 0), color: Theme.error }
                        ]
                        delegate: ColumnLayout {
                            spacing: 2
                            Text { text: modelData.value; color: modelData.color; font.pixelSize: 20; font.bold: true }
                            Text { text: modelData.label; color: Theme.textMuted; font.pixelSize: 10 }
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        visible: !!root.st.listing || (root.st.is_paused && root.st.active > 0) || root.st.running
                        text: root.st.listing ? root.st.listing + "..."
                              : (root.st.is_paused ? "Paused" : "Running")
                        color: root.st.is_paused ? Theme.warning : Theme.primaryLight
                        font.pixelSize: 12
                        font.bold: true
                    }
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    ActionButton {
                        visible: !root.st.is_paused
                        text: "Pause"
                        icon: Icons.pause
                        primary: true
                        enabled: (root.st.active || 0) > 0
                        onClicked: Bridge.queuePause()
                    }
                    ActionButton {
                        visible: !!root.st.is_paused
                        text: "Resume"
                        icon: Icons.play
                        primary: true
                        enabled: (root.st.active || 0) > 0
                        onClicked: Bridge.queueResume()
                    }
                    ActionButton {
                        text: "Retry failed (" + (root.st.failed || 0) + ")"
                        icon: Icons.rotate
                        enabled: (root.st.failed || 0) > 0
                        onClicked: Bridge.queueRetryFailed()
                    }
                    ActionButton {
                        text: "Clear finished"
                        icon: Icons.trash
                        enabled: ((root.st.done || 0) + (root.st.skipped || 0)) > 0
                        onClicked: Bridge.queueClearFinished()
                    }
                    Item { width: 12; height: 1 }
                    Repeater {
                        model: [
                            { key: "all", label: "All" },
                            { key: "waiting", label: "Waiting" },
                            { key: "failed", label: "Failed" },
                            { key: "done", label: "Finished" }
                        ]
                        delegate: ActionButton {
                            text: modelData.label
                            checked: root.filter === modelData.key
                            onClicked: root.filter = modelData.key
                        }
                    }
                }
            }
        }

        // Empty state
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.shown.length === 0
            spacing: 10
            Item { Layout.fillHeight: true }
            FaIcon { icon: Icons.listOl; size: 40; iconColor: Theme.border; Layout.alignment: Qt.AlignHCenter }
            Text {
                text: (Bridge.queueItems || []).length === 0 ? "The download queue is empty" : "Nothing in this filter"
                color: Theme.textPrimary; font.pixelSize: 14; font.bold: true
                Layout.alignment: Qt.AlignHCenter
            }
            Text {
                visible: (Bridge.queueItems || []).length === 0
                text: "In Categories & Feeds, use Download selected, Whole sub-category, Whole category\nor Several categories... to add articles here."
                color: Theme.textMuted; font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                Layout.alignment: Qt.AlignHCenter
            }
            Item { Layout.fillHeight: true }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.shown.length > 0
            clip: true
            spacing: 6
            model: root.shown
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Rectangle {
                id: row
                readonly property var it: modelData
                readonly property bool current: it.status === "downloading" && root.prog.id === it.id
                readonly property real bytesDone: current ? (root.prog.done || 0) : (it.bytes_done || 0)
                readonly property real bytesTotal: current ? (root.prog.total || 0) : (it.bytes_total || 0)
                readonly property bool showBar: it.status === "downloading" || (it.status === "paused" && bytesTotal > 0)

                width: list.width - 10
                height: 66
                radius: Theme.radiusMd
                color: Theme.card
                border.color: it.status === "downloading" ? Theme.primary : Theme.border

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 10
                    spacing: 12

                    FaIcon { icon: root.statusIcon(row.it.status); size: 14; iconColor: root.statusColor(row.it.status) }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Text {
                            text: row.it.title
                            color: Theme.textPrimary; font.pixelSize: 12; font.bold: true
                            elide: Text.ElideRight; Layout.fillWidth: true
                        }
                        Text {
                            text: row.it.category + " › " + row.it.subcategory + "   •   "
                                  + (row.it.status === "downloading" && row.bytesDone > 0
                                     ? "Downloading model  " + root.fmtBytes(row.bytesDone) + (row.bytesTotal ? " / " + root.fmtBytes(row.bytesTotal) : "")
                                     : root.statusText(row.it))
                            color: row.it.status === "failed" ? Theme.error : Theme.textMuted
                            font.pixelSize: 10
                            elide: Text.ElideRight; Layout.fillWidth: true
                        }
                        Rectangle {
                            visible: row.showBar
                            Layout.fillWidth: true
                            height: 4; radius: 2
                            color: Theme.surfaceElevated
                            Rectangle {
                                height: parent.height; radius: 2
                                width: row.bytesTotal > 0 ? parent.width * Math.min(1, row.bytesDone / row.bytesTotal) : parent.width * 0.15
                                color: row.it.status === "paused" ? Theme.warning : Theme.primary
                            }
                        }
                    }

                    ActionButton {
                        visible: row.it.status === "failed"
                        text: "Retry"
                        icon: Icons.rotate
                        onClicked: Bridge.queueRetry(row.it.id)
                    }
                    ActionButton {
                        visible: row.it.status === "pending" || row.it.status === "paused"
                        text: "Next"
                        icon: Icons.arrowUp
                        onClicked: Bridge.queueMoveToTop(row.it.id)
                    }
                    ActionButton {
                        visible: (row.it.status === "done" || row.it.status === "skipped") && !!row.it.folder
                        text: "Open"
                        icon: Icons.folderOpen
                        onClicked: Bridge.openFolder(row.it.folder)
                    }
                    ActionButton {
                        visible: row.it.status !== "downloading"
                        text: ""
                        icon: Icons.times
                        onClicked: Bridge.queueRemove(row.it.id)
                    }
                }
            }
        }
    }
}
