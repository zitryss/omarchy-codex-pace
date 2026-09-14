import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import qs.Commons

Column {
    id: root
    required property string label
    required property string reading
    property var fraction: null
    property bool countdown: false
    property string explanation: ""
    property color foreground: Color.foreground
    property color background: Color.popups.background
    readonly property bool known: fraction !== null && isFinite(fraction)
    readonly property real bounded: known ? Math.max(0, Math.min(1, fraction)) : 0
    readonly property bool dark: background.hslLightness < 0.5
    readonly property color green: dark ? "#91bc91" : "#28733e"
    readonly property color red: dark ? "#d87979" : "#b13c46"
    readonly property color gray: dark ? "#9299a3" : "#737b85"
    readonly property color fillColor: !known ? gray : countdown ? blend(green, gray, bounded) : blend(red, green, bounded)
    function blend(a, b, t) { return Qt.rgba(a.r+(b.r-a.r)*t, a.g+(b.g-a.g)*t, a.b+(b.b-a.b)*t, 1) }
    spacing: Style.space(6)
    Accessible.name: label + ": " + reading
    Accessible.description: explanation
    HoverHandler { id: hover }
    ToolTip.visible: hover.hovered && explanation !== ""
    ToolTip.delay: 550
    ToolTip.text: explanation
    RowLayout {
        width: parent.width
        Text {
            text: root.label
            color: root.foreground
            font.family: Style.font.family
            font.pixelSize: Style.font.body
            textFormat: Text.PlainText
            Layout.fillWidth: true
        }
        Text {
            text: root.reading
            color: root.foreground
            font.family: Style.font.family
            font.pixelSize: Style.font.body
            font.bold: true
            textFormat: Text.PlainText
        }
    }
    Rectangle {
        width: parent.width
        height: Style.space(5)
        radius: height / 2
        color: Qt.alpha(root.foreground, 0.12)
        Rectangle {
            width: parent.width * root.bounded
            height: parent.height
            radius: parent.radius
            color: root.fillColor
        }
    }
}
