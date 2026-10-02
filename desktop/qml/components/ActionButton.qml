import QtQuick 2.15
import QtQuick.Layouts 1.15
import ".."

// Compact text button with optional icon, used for toolbar-style actions.
Rectangle {
    id: root
    property string text: ""
    property string icon: ""
    property bool primary: false
    property bool danger: false
    property bool checked: false   // renders as an "on" toggle chip
    signal clicked()

    implicitHeight: 36
    implicitWidth: row.implicitWidth + 24
    radius: Theme.radiusSm
    opacity: enabled ? 1.0 : 0.45
    color: {
        if (root.primary) return mouse.containsMouse ? Theme.primaryHover : Theme.primary
        if (root.danger) return mouse.containsMouse ? Qt.rgba(Theme.error.r, Theme.error.g, Theme.error.b, 0.3) : Qt.rgba(Theme.error.r, Theme.error.g, Theme.error.b, 0.15)
        if (root.checked) return Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.22)
        return mouse.containsMouse ? Theme.surfaceElevated : Theme.card
    }
    border.color: root.checked ? Theme.primary : (root.primary ? "transparent" : Theme.border)
    border.width: 1

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: 7
        FaIcon {
            visible: root.icon !== ""
            icon: root.icon
            size: 11
            iconColor: root.primary ? "white" : (root.danger ? Theme.error : (root.checked ? Theme.primaryLight : Theme.textSecondary))
        }
        Text {
            text: root.text
            color: root.primary ? "white" : (root.danger ? Theme.error : (root.checked ? Theme.primaryLight : Theme.textSecondary))
            font.pixelSize: 11
            font.bold: true
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
