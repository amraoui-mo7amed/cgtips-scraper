import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import "../components"
import ".."

// The download queue: everything waiting, downloading, finished or failed.
Item {
    id: root

    signal openMissingModelsRequested()

    readonly property var st: Bridge.queueStats || ({})
    readonly property var prog: Bridge.queueProgress || ({})
    property string filter: "all"   // all | waiting | done | no_model | failed

    readonly property var shown: {
        var out = []
        var items = Bridge.queueItems || []
        for (var i = 0; i < items.length; ++i) {
            var s = items[i].status
            if (root.filter === "waiting" && !(s === "pending" || s === "paused" || s === "downloading")) continue
            if (root.filter === "no_model" && s !== "no_model") continue
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
            case "no_model": return "#F59E0B"
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
            case "no_model": return Icons.box
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
            case "no_model": return it.error || "No 3D model available"
            case "failed": return it.error || "Failed"
            default: return "Waiting"
        }
    }

    function providerName(it) {
        if (!it) return "Google Drive";
        var p = it.provider || "";
        if (!p && it.gdrive_url) {
            var u = (it.gdrive_url || "").toLowerCase();
            if (u.indexOf("fshare.vn") !== -1) p = "Fshare";
            else if (u.indexOf("sharepoint.com") !== -1) p = "SharePoint";
            else if (u.indexOf("onedrive") !== -1 || u.indexOf("1drv.ms") !== -1) p = "OneDrive";
            else if (u.indexOf("drive.google.com") !== -1 || u.indexOf("google.com") !== -1) p = "Google Drive";
            else p = "Direct Link";
        }
        if (!p) {
            p = "Google Drive";
        }
        return p;
    }

    function providerBg(it) {
        var p = (providerName(it) || "").toLowerCase();
        if (p.indexOf("fshare") !== -1) return "#7F1D1D";
        if (p.indexOf("sharepoint") !== -1 || p.indexOf("onedrive") !== -1) return "#0C4A6E";
        if (p.indexOf("drive") !== -1 || p.indexOf("gdrive") !== -1) return "#1E3A8A";
        return "#134E4A";
    }

    function providerBorder(it) {
        var p = (providerName(it) || "").toLowerCase();
        if (p.indexOf("fshare") !== -1) return "#EF4444";
        if (p.indexOf("sharepoint") !== -1 || p.indexOf("onedrive") !== -1) return "#0284C7";
        if (p.indexOf("drive") !== -1 || p.indexOf("gdrive") !== -1) return "#3B82F6";
        return "#14B8A6";
    }

    function providerIcon(it) {
        var p = (providerName(it) || "").toLowerCase();
        if (p.indexOf("fshare") !== -1) return Icons.fire;
        if (p.indexOf("sharepoint") !== -1 || p.indexOf("onedrive") !== -1) return Icons.cloud;
        if (p.indexOf("drive") !== -1 || p.indexOf("gdrive") !== -1) return Icons.cloud;
        return Icons.hdd;
    }

    function providerIconColor(it) {
        var p = (providerName(it) || "").toLowerCase();
        if (p.indexOf("fshare") !== -1) return "#FCA5A5";
        if (p.indexOf("sharepoint") !== -1 || p.indexOf("onedrive") !== -1) return "#38BDF8";
        if (p.indexOf("drive") !== -1 || p.indexOf("gdrive") !== -1) return "#60A5FA";
        return "#2DD4BF";
    }

    function providerTextColor(it) {
        var p = (providerName(it) || "").toLowerCase();
        if (p.indexOf("fshare") !== -1) return "#FEE2E2";
        if (p.indexOf("sharepoint") !== -1 || p.indexOf("onedrive") !== -1) return "#E0F2FE";
        if (p.indexOf("drive") !== -1 || p.indexOf("gdrive") !== -1) return "#DBEAFE";
        return "#CCFBF1";
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
                            { label: "No Model", value: (root.st.no_model || 0), color: "#F59E0B" },
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
                        text: "Retry no model (" + (root.st.no_model || 0) + ")"
                        icon: Icons.rotate
                        visible: (root.st.no_model || 0) > 0
                        enabled: (root.st.no_model || 0) > 0
                        onClicked: Bridge.queueRetryNoModel()
                    }
                    ActionButton {
                        text: "Retry failed (" + (root.st.failed || 0) + ")"
                        icon: Icons.rotate
                        visible: (root.st.failed || 0) > 0
                        enabled: (root.st.failed || 0) > 0
                        onClicked: Bridge.queueRetryFailed()
                    }
                    ActionButton {
                        text: "Clear finished"
                        icon: Icons.trash
                        enabled: ((root.st.done || 0) + (root.st.skipped || 0)) > 0
                        onClicked: Bridge.queueClearFinished()
                    }
                    ActionButton {
                        text: "Clear all"
                        icon: Icons.trash
                        enabled: (root.st.total || 0) > 0
                        onClicked: confirmClearModal.open()
                    }
                    ActionButton {
                        text: "Missing Models" + (Bridge.missingModelsCount > 0 ? " (" + Bridge.missingModelsCount + ")" : "")
                        icon: Icons.exclamationTriangle
                        visible: true
                        onClicked: root.openMissingModelsRequested()
                    }
                    ActionButton {
                        text: "Change Storage"
                        icon: Icons.folder
                        onClicked: Bridge.chooseStorageDir(false)
                    }
                    Item { width: 12; height: 1 }
                    Repeater {
                        model: [
                            { key: "all", label: "All" },
                            { key: "waiting", label: "Waiting" },
                            { key: "done", label: "Finished" },
                            { key: "no_model", label: "No Model" + ((root.st.no_model || 0) > 0 ? " (" + root.st.no_model + ")" : "") },
                            { key: "failed", label: "Failed" + ((root.st.failed || 0) > 0 ? " (" + root.st.failed + ")" : "") }
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
                height: 68
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
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            // Provider Badge (Google Drive / Fshare / SharePoint)
                            Rectangle {
                                visible: !!root.providerName(row.it)
                                height: 18
                                width: Math.max(22, queueProvBadgeRow.implicitWidth + 12)
                                radius: 4
                                color: root.providerBg(row.it)
                                border.color: root.providerBorder(row.it)
                                border.width: 1

                                RowLayout {
                                    id: queueProvBadgeRow
                                    anchors.centerIn: parent
                                    spacing: 4
                                    FaIcon {
                                        icon: root.providerIcon(row.it)
                                        size: 8
                                        iconColor: root.providerIconColor(row.it)
                                    }
                                    Text {
                                        text: root.providerName(row.it)
                                        color: root.providerTextColor(row.it)
                                        font.pixelSize: 9
                                        font.bold: true
                                    }
                                }
                            }

                            Text {
                                text: (row.it.category ? (row.it.category + " › " + row.it.subcategory) : "Direct Download")
                                      + "   •   "
                                      + (row.it.status === "downloading" && row.bytesDone > 0
                                         ? "Downloading model  " + root.fmtBytes(row.bytesDone) + (row.bytesTotal ? " / " + root.fmtBytes(row.bytesTotal) : "")
                                         : root.statusText(row.it))
                                color: row.it.status === "failed" ? Theme.error : (row.it.status === "no_model" ? "#F59E0B" : Theme.textMuted)
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
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
                        visible: row.it.status === "failed" || row.it.status === "no_model"
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
                        visible: (row.it.status === "done" || row.it.status === "skipped" || row.it.status === "no_model") && !!row.it.folder
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

    // Confirm Clear All Queue Modal
    Rectangle {
        id: confirmClearModal
        anchors.fill: parent
        color: "#D9050811"
        z: 999
        visible: opacity > 0
        opacity: 0

        Behavior on opacity { NumberAnimation { duration: 150 } }

        function open() { opacity = 1 }
        function close() { opacity = 0 }

        MouseArea { anchors.fill: parent; onClicked: confirmClearModal.close() }

        Rectangle {
            width: Math.min(parent.width - 40, 460)
            height: confirmCol.implicitHeight + 40
            anchors.centerIn: parent
            radius: Theme.radiusLg
            color: Theme.surface
            border.color: Theme.border
            border.width: 1

            MouseArea { anchors.fill: parent; onClicked: {} }

            ColumnLayout {
                id: confirmCol
                anchors.fill: parent
                anchors.margins: 20
                spacing: 16

                RowLayout {
                    spacing: 12
                    Rectangle {
                        width: 40
                        height: 40
                        radius: Theme.radiusMd
                        color: Qt.rgba(Theme.danger.r, Theme.danger.g, Theme.danger.b, 0.15)
                        FaIcon {
                            anchors.centerIn: parent
                            icon: Icons.trash
                            size: 18
                            iconColor: Theme.danger
                        }
                    }
                    ColumnLayout {
                        spacing: 2
                        Text {
                            text: "Clear Download Queue?"
                            color: Theme.textPrimary
                            font.pixelSize: 15
                            font.bold: true
                        }
                        Text {
                            text: "Cancel in-progress download and wipe all items"
                            color: Theme.textMuted
                            font.pixelSize: 11
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: "Are you sure you want to clear all " + (root.st.total || 0) + " items from the download queue? Active downloads will be stopped and all waiting items will be removed so you can queue other items."
                    color: Theme.textSecondary
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Item { Layout.fillWidth: true }
                    ActionButton {
                        text: "Cancel"
                        icon: Icons.times
                        onClicked: confirmClearModal.close()
                    }
                    ActionButton {
                        text: "Yes, Clear All"
                        icon: Icons.trash
                        primary: true
                        onClicked: {
                            confirmClearModal.close()
                            Bridge.queueClearAll()
                        }
                    }
                }
            }
        }
    }
}
