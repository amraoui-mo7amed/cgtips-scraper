import QtQuick 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."

// Global status strip for the download queue, shown on every tab while it has work.
Rectangle {
    id: root
    readonly property var st: Bridge.queueStats || ({})
    readonly property var prog: Bridge.queueProgress || ({})
    readonly property bool running: !!st.running
    readonly property bool paused: !!st.is_paused && (st.active || 0) > 0
    readonly property bool active: running || paused || !!st.listing

    signal openQueueRequested()

    visible: active
    implicitHeight: active ? 62 : 0
    color: Theme.surface
    border.color: Theme.border
    border.width: 1

    function fmtBytes(b) {
        if (!b) return "0 B"
        var u = ["B", "KB", "MB", "GB"], i = 0
        while (b >= 1024 && i < u.length - 1) { b /= 1024; i++ }
        return b.toFixed(i >= 2 ? 1 : 0) + " " + u[i]
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 18
        anchors.rightMargin: 14
        spacing: 14

        FaIcon {
            icon: root.paused ? Icons.pause : Icons.download
            size: 18
            iconColor: root.paused ? Theme.warning : Theme.primaryLight
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5

            Text {
                Layout.fillWidth: true
                elide: Text.ElideRight
                color: Theme.textPrimary
                font.pixelSize: 12
                font.bold: true
                text: {
                    var head = "Download queue — " + (root.st.finished || 0) + " / " + (root.st.total || 0)
                    if (root.paused && !root.running) return head + "   Paused, " + root.st.active + " waiting"
                    if (root.st.listing && !root.st.current_title) return head + "   " + root.st.listing + "..."
                    var line = head + "   " + (root.st.current_title || "")
                    if (root.prog.id && root.prog.id === root.st.current_id && root.prog.done > 0)
                        line += "  (" + root.fmtBytes(root.prog.done) + (root.prog.total ? " / " + root.fmtBytes(root.prog.total) : "") + ")"
                    return line
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 6
                radius: 3
                color: Theme.surfaceElevated
                Rectangle {
                    height: parent.height
                    radius: 3
                    width: root.st.total > 0 ? parent.width * Math.min(1, root.st.finished / root.st.total) : 0
                    color: root.paused ? Theme.warning : Theme.primary
                    Behavior on width { NumberAnimation { duration: 200 } }
                }
            }
        }

        ActionButton {
            visible: !root.st.is_paused
            text: "Pause"
            icon: Icons.pause
            onClicked: Bridge.queuePause()
        }
        ActionButton {
            visible: !!root.st.is_paused
            text: "Resume"
            icon: Icons.play
            primary: true
            onClicked: Bridge.queueResume()
        }
        ActionButton {
            text: "Open queue"
            icon: Icons.listOl
            onClicked: root.openQueueRequested()
        }
    }
}
