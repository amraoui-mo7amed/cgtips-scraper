import QtQuick 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."

// Global status strip for a running / finished bulk download.
Rectangle {
    id: root
    readonly property var st: Bridge.bulkState || ({})
    readonly property bool active: st.phase !== undefined
    readonly property bool running: !!st.running

    visible: active
    implicitHeight: active ? 62 : 0
    color: Theme.surface
    border.color: Theme.border
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 18
        anchors.rightMargin: 14
        spacing: 14

        FaIcon {
            icon: root.running ? Icons.download : (root.st.failed > 0 || root.st.cancelled ? Icons.exclamationTriangle : Icons.checkCircle)
            size: 18
            iconColor: root.running ? Theme.primaryLight : (root.st.failed > 0 || root.st.cancelled ? Theme.warning : Theme.success)
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
                    if (root.running) {
                        if (root.st.phase === "listing") return "Bulk download — " + (root.st.current || "reading feeds...")
                        return "Bulk download — " + root.st.done + " / " + root.st.total + "   " + (root.st.current || "")
                    }
                    return (root.st.cancelled ? "Cancelled" : "Finished") + " — " + root.st.succeeded + " downloaded, "
                        + root.st.skipped + " skipped, " + root.st.failed + " failed"
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
                    width: root.st.total > 0 ? parent.width * Math.min(1, root.st.done / root.st.total) : 0
                    color: root.running ? Theme.primary : Theme.success
                    Behavior on width { NumberAnimation { duration: 200 } }
                }
                // indeterminate while the feeds are being listed
                Rectangle {
                    visible: root.running && root.st.phase === "listing"
                    height: parent.height
                    width: parent.width * 0.2
                    radius: 3
                    color: Theme.primary
                    SequentialAnimation on x {
                        running: root.running && root.st.phase === "listing"
                        loops: Animation.Infinite
                        NumberAnimation { from: 0; to: 300; duration: 900 }
                    }
                }
            }
        }

        ActionButton {
            visible: root.running
            text: "Cancel"
            icon: Icons.stop
            danger: true
            onClicked: Bridge.cancelBulk()
        }
        ActionButton {
            visible: !root.running
            text: "Dismiss"
            onClicked: Bridge.dismissBulk()
        }
    }
}
