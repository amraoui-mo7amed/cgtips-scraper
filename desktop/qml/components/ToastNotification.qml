import QtQuick 2.15
import QtQuick.Controls 2.15
import ".."
import "."

Item {
    id: root
    width: 320
    height: 60
    anchors.top: parent.top
    anchors.right: parent.right
    anchors.topMargin: 20
    anchors.rightMargin: 20
    z: 9999

    property string message: ""
    property string type: "info" // 'info', 'success', 'warning', 'error'
    property bool showing: false

    function showToast(toastType, toastMsg) {
        type = toastType
        message = toastMsg
        showing = true
        hideTimer.restart()
    }

    Timer {
        id: hideTimer
        interval: 3500
        onTriggered: root.showing = false
    }

    Rectangle {
        id: toastBox
        anchors.fill: parent
        radius: Theme.radiusMd
        color: Theme.surfaceElevated
        border.color: {
            if (root.type === "success") return Theme.success;
            if (root.type === "error") return Theme.error;
            if (root.type === "warning") return Theme.warning;
            return Theme.primaryLight;
        }
        border.width: 1

        opacity: root.showing ? 1.0 : 0.0
        scale: root.showing ? 1.0 : 0.9
        Behavior on opacity { NumberAnimation { duration: 200 } }
        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }

        Row {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12

            FaIcon {
                anchors.verticalCenter: parent.verticalCenter
                icon: {
                    if (root.type === "success") return Icons.checkCircle;
                    if (root.type === "error") return Icons.timesCircle;
                    if (root.type === "warning") return Icons.exclamationTriangle;
                    return Icons.infoCircle;
                }
                size: 16
                iconColor: {
                    if (root.type === "success") return Theme.success;
                    if (root.type === "error") return Theme.error;
                    if (root.type === "warning") return Theme.warning;
                    return Theme.primaryLight;
                }
            }

            Text {
                text: root.message
                color: Theme.textPrimary
                font.pixelSize: 12
                font.weight: Font.DemiBold
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - 50
                wrapMode: Text.Wrap
                elide: Text.ElideRight
                maximumLineCount: 2
            }
        }
    }
}
