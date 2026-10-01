import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import ".."

Rectangle {
    id: root
    anchors.fill: parent
    color: Qt.rgba(0, 0, 0, 0.92)
    z: 10000
    visible: opacity > 0
    opacity: 0

    property var images: []
    property int currentIndex: 0
    property string title: ""

    Behavior on opacity { NumberAnimation { duration: 200 } }

    function open(imgs, titleText, startIdx) {
        images = imgs || []
        title = titleText || ""
        currentIndex = startIdx || 0
        opacity = 1
        root.forceActiveFocus()
    }

    function close() {
        opacity = 0
    }

    // Keyboard navigation
    Keys.onLeftPressed: prevImage()
    Keys.onRightPressed: nextImage()
    Keys.onEscapePressed: close()

    function prevImage() {
        if (images.length > 0) {
            currentIndex = (currentIndex - 1 + images.length) % images.length
        }
    }

    function nextImage() {
        if (images.length > 0) {
            currentIndex = (currentIndex + 1) % images.length
        }
    }

    MouseArea {
        anchors.fill: parent
        onClicked: root.close()
    }

    // Top Header Bar
    Rectangle {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60
        color: Qt.rgba(0, 0, 0, 0.6)

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 24
            anchors.rightMargin: 24

            ColumnLayout {
                spacing: 2
                Text {
                    text: root.title
                    color: "white"
                    font.pixelSize: 14
                    font.bold: true
                    elide: Text.ElideRight
                    Layout.maximumWidth: root.width - 150
                }
                Text {
                    text: (root.images.length > 0) ? ("Photo " + (root.currentIndex + 1) + " of " + root.images.length) : ""
                    color: Theme.textSecondary
                    font.pixelSize: 11
                }
            }

            Item { Layout.fillWidth: true }

            Rectangle {
                width: 36
                height: 36
                radius: 18
                color: Qt.rgba(1, 1, 1, 0.1)

                FaIcon {
                    anchors.centerIn: parent
                    icon: Icons.times
                    size: 14
                    iconColor: "white"
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.close()
                }
            }
        }
    }

    // Main Image Canvas
    Item {
        anchors.fill: parent
        anchors.topMargin: 70
        anchors.bottomMargin: 70
        anchors.leftMargin: 80
        anchors.rightMargin: 80

        Image {
            id: currentImg
            anchors.centerIn: parent
            width: Math.min(parent.width, implicitWidth)
            height: Math.min(parent.height, implicitHeight)
            fillMode: Image.PreserveAspectFit
            source: (root.images.length > root.currentIndex) ? root.images[root.currentIndex] : ""
            asynchronous: true

            MouseArea {
                anchors.fill: parent
                // absorb clicks so clicking the photo doesn't close modal
                onClicked: {}
            }
        }
    }

    // Previous Arrow
    Rectangle {
        visible: root.images.length > 1
        anchors.left: parent.left
        anchors.leftMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        width: 44
        height: 44
        radius: 22
        color: Qt.rgba(1, 1, 1, 0.15)

        FaIcon {
            anchors.centerIn: parent
            icon: Icons.chevronLeft
            size: 16
            iconColor: "white"
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.prevImage()
        }
    }

    // Next Arrow
    Rectangle {
        visible: root.images.length > 1
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        width: 44
        height: 44
        radius: 22
        color: Qt.rgba(1, 1, 1, 0.15)

        FaIcon {
            anchors.centerIn: parent
            icon: Icons.chevronRight
            size: 16
            iconColor: "white"
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.nextImage()
        }
    }
}

