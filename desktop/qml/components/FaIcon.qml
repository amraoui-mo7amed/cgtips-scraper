import QtQuick 2.15
import ".."

Text {
    id: root
    property string icon: ""
    property int size: 14
    property color iconColor: Theme.textPrimary
    property bool solid: true

    text: root.icon
    font.family: "Font Awesome 6 Free"
    font.pixelSize: root.size
    font.weight: root.solid ? Font.Black : Font.Normal
    color: root.iconColor
    horizontalAlignment: Text.AlignHCenter
    verticalAlignment: Text.AlignVCenter
}
