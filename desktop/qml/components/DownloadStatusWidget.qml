import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import CGTips 1.0
import ".."
import "."

// Header button showing running downloads / imports, with a popup listing every job.
Rectangle {
    id: root
    readonly property var jobs: Bridge.downloadJobs || []
    readonly property int activeCount: Bridge.activeJobCount
    // newest running job if any, otherwise the newest job
    readonly property var latest: {
        for (var i = 0; i < jobs.length; i++)
            if (jobs[i].status === "running") return jobs[i]
        return jobs.length > 0 ? jobs[0] : null
    }
    property real pulse: 1.0

    SequentialAnimation on pulse {
        running: root.activeCount > 0
        loops: Animation.Infinite
        NumberAnimation { to: 0.35; duration: 600 }
        NumberAnimation { to: 1.0; duration: 600 }
    }

    implicitWidth: Math.min(190, Math.max(120, statusRow.implicitWidth + 24))
    implicitHeight: 36
    radius: Theme.radiusMd
    color: btnMouse.containsMouse || popup.opened ? Theme.surfaceElevated : Theme.surface
    border.color: root.activeCount > 0 ? Theme.primary : Theme.border
    clip: true

    function statusColor(s) {
        if (s === "running") return Theme.primaryLight
        if (s === "done") return Theme.success
        if (s === "cancelled") return Theme.warning
        return Theme.error
    }
    function statusIcon(s) {
        if (s === "running") return Icons.download
        if (s === "done") return Icons.checkCircle
        if (s === "cancelled") return Icons.stop
        return Icons.exclamationTriangle
    }

    // Thin progress line along the bottom of the button for the newest running job
    Rectangle {
        visible: root.activeCount > 0 && root.latest && root.latest.progress >= 0
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        height: 3
        width: root.latest ? parent.width * Math.min(1, Math.max(0, root.latest.progress)) : 0
        color: Theme.primary
        Behavior on width { NumberAnimation { duration: 200 } }
    }

    RowLayout {
        id: statusRow
        anchors.centerIn: parent
        spacing: 7

        FaIcon {
            icon: root.activeCount > 0 ? Icons.download : (root.latest ? root.statusIcon(root.latest.status) : Icons.download)
            size: 12
            iconColor: root.activeCount > 0 ? Theme.primaryLight : (root.latest ? root.statusColor(root.latest.status) : Theme.textMuted)
            opacity: root.activeCount > 0 ? root.pulse : 1.0
        }
        Text {
            text: {
                if (root.activeCount > 0) {
                    var j = root.latest
                    var pct = (j && j.progress >= 0) ? "  " + Math.round(j.progress * 100) + "%" : ""
                    return (root.activeCount > 1 ? root.activeCount + " downloads" : "Downloading") + pct
                }
                return root.jobs.length > 0 ? "Downloads" : "No downloads"
            }
            color: root.activeCount > 0 ? Theme.primaryLight : Theme.textSecondary
            font.pixelSize: 11
            font.bold: true
        }
    }

    MouseArea {
        id: btnMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: popup.opened ? popup.close() : popup.open()
    }

    Popup {
        id: popup
        objectName: "downloadPopup"
        y: root.height + 6
        x: root.width - width
        width: 400
        height: Math.min(470, 64 + Math.max(60, root.jobs.length * 76))
        padding: 12
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

        background: Rectangle {
            color: Theme.surface
            radius: Theme.radiusMd
            border.color: Theme.border
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 8

            RowLayout {
                id: header
                Layout.fillWidth: true
                Text {
                    text: "Download status"
                    color: Theme.textPrimary
                    font.pixelSize: 13
                    font.bold: true
                    Layout.fillWidth: true
                }
                ActionButton {
                    visible: root.jobs.length > root.activeCount
                    implicitHeight: 26
                    text: "Clear finished"
                    onClicked: Bridge.clearFinishedJobs()
                }
            }

            Text {
                visible: root.jobs.length === 0
                text: "Nothing yet. Downloads from the resolver, bulk\ndownloads and library imports show up here."
                color: Theme.textMuted
                font.pixelSize: 11
                Layout.topMargin: 10
                Layout.alignment: Qt.AlignHCenter
                horizontalAlignment: Text.AlignHCenter
            }

            ListView {
                id: jobList
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: root.jobs.length > 0
                clip: true
                spacing: 6
                model: root.jobs
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                delegate: Rectangle {
                    width: jobList.width
                    height: jobCol.implicitHeight + 16
                    radius: Theme.radiusSm
                    color: Theme.card
                    border.color: modelData.status === "running" ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.5) : Theme.border

                    ColumnLayout {
                        id: jobCol
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 7
                            FaIcon {
                                icon: modelData.kind === "import" ? Icons.fileImport : root.statusIcon(modelData.status)
                                size: 11
                                iconColor: root.statusColor(modelData.status)
                            }
                            Text {
                                text: modelData.title
                                color: Theme.textPrimary
                                font.pixelSize: 11
                                font.bold: true
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            Text {
                                text: modelData.status === "running"
                                      ? (modelData.progress >= 0 ? Math.round(modelData.progress * 100) + "%" : "…")
                                      : modelData.status
                                color: root.statusColor(modelData.status)
                                font.pixelSize: 10
                                font.bold: true
                            }
                        }

                        Rectangle {
                            visible: modelData.status === "running" || modelData.progress >= 0
                            Layout.fillWidth: true
                            height: 4
                            radius: 2
                            color: Theme.surfaceElevated
                            clip: true
                            Rectangle {
                                visible: modelData.progress >= 0
                                height: parent.height
                                radius: 2
                                width: parent.width * Math.min(1, Math.max(0, modelData.progress))
                                color: root.statusColor(modelData.status)
                            }
                            // indeterminate shimmer
                            Rectangle {
                                visible: modelData.status === "running" && modelData.progress < 0
                                height: parent.height
                                width: parent.width * 0.25
                                radius: 2
                                color: Theme.primary
                                SequentialAnimation on x {
                                    running: modelData.status === "running" && modelData.progress < 0
                                    loops: Animation.Infinite
                                    NumberAnimation { from: -40; to: 360; duration: 1100 }
                                }
                            }
                        }

                        Text {
                            text: modelData.started + "  ·  " + (modelData.detail || "")
                            color: modelData.status === "failed" ? Theme.error : Theme.textMuted
                            font.pixelSize: 10
                            wrapMode: Text.Wrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            Layout.preferredWidth: jobList.width - 16
                        }
                    }
                }
            }
        }
    }
}
