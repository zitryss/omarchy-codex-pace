pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
    id: root
    moduleName: "c3po.codex-pace"
    manageIpc: false
    property var shell: null
    readonly property var service: shell ? shell.serviceFor(moduleName) : (bar && bar.shell ? bar.shell.serviceFor(moduleName) : null)
    readonly property var view: service ? service.view : ({status: "Collector unavailable", cells: []})
    readonly property color fg: Color.foreground
    readonly property color muted: Qt.alpha(fg, 0.60)
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    function val(key) { return view[key] === undefined ? "—" : String(view[key]) }
    function pct(key) { return val(key) === "—" ? "—" : val(key) + "%" }
    onOpenedChanged: if (opened && service) service.refresh()

    // IPC belongs to the visual scene; one distinct endpoint per monitor.
    IpcHandler {
        enabled: !!root.QsWindow.window && !!root.QsWindow.window.screen
        target: root.moduleName + "." + (root.QsWindow.window?.screen?.name || "pending")
        function status(): string { return JSON.stringify({opened: root.opened, scrollY: flick.contentY, contentHeight: flick.contentHeight, viewportHeight: flick.height, view: root.view}) }
        function open(): void { root.open() }
        function close(): void { root.close() }
        function preview(name: string): string { return root.service ? root.service.preview(name) : "unavailable" }
        function clearPreview(): void { if (root.service) root.service.clearPreview() }
    }

    component Label: Text {
        color: root.fg
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        textFormat: Text.PlainText
    }
    BarIconButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "󰔟"
        tooltipText: "Codex Pace · " + root.pct("daily") + " today\n" + root.val("status")
        Accessible.name: "Codex Pace"
        Accessible.description: "Open subscription pacing"
        activeFocusOnTab: true
        Keys.onReturnPressed: root.toggle()
        Keys.onSpacePressed: root.toggle()
        onPressed: root.toggle()
    }
    KeyboardPanel {
        id: popup
        anchorItem: button
        owner: root
        bar: root.bar
        open: root.opened
        focusTarget: keys
        contentWidth: fittedContentWidth(Style.space(470))
        contentHeight: fittedContentHeight(content.implicitHeight, Style.space(720))
        PanelKeyCatcher {
            id: keys
            anchors.fill: parent
            onCloseRequested: root.close()
            onTabRequested: direction => root.switchPanel(direction)
            onActivateRequested: { if (root.service) root.service.refresh() }
            onMoveRequested: (dx, dy) => {
                flick.contentY = Math.max(0, Math.min(flick.contentHeight - flick.height, flick.contentY + dy * Style.space(45)))
            }
            onTextKey: text => { if ((text === "r" || text === "R") && root.service) root.service.refresh() }
            Flickable {
                id: flick
                anchors.fill: parent
                contentHeight: content.implicitHeight
                contentWidth: width
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                Column {
                    id: content
                    width: parent.width
                    spacing: Style.space(16)
                    Label { text: root.view.fixture ? "Codex Pace · TEST FIXTURE: " + root.view.fixture : "Codex Pace"; font.bold: true; font.pixelSize: Style.font.body + 2 }
                    GridLayout {
                        width: parent.width
                        columns: width < Style.space(360) ? 1 : 3
                        columnSpacing: Style.space(18)
                        rowSpacing: Style.space(12)
                        Repeater {
                            model: [
                                {label: "Available today", value: root.pct("available"), sub: "of weekly quota"},
                                {label: "Day ends in", value: root.val("countdown"), sub: ""},
                                {label: "Weekly reset", value: root.val("days"), sub: "days left"}
                            ]
                            ColumnLayout {
                                id: metric
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                spacing: Style.space(5)
                                Label { text: metric.modelData.label; color: root.muted; font.pixelSize: Style.font.body - 1 }
                                Label { text: metric.modelData.value; font.pixelSize: Style.font.body + 12; font.bold: true }
                                Label { text: metric.modelData.sub; color: root.muted; font.pixelSize: Style.font.body - 2 }
                            }
                        }
                    }
                    Column {
                        width: parent.width
                        spacing: Style.space(10)
                        Repeater {
                            model: [
                                {label: "Today's allowance left", value: root.pct("daily"), fill: root.view.dailyFill || 0},
                                {label: "Weekly allowance left", value: root.pct("weekly"), fill: root.view.weeklyFill || 0}
                            ]
                            Column {
                                id: allowance
                                required property var modelData
                                width: parent.width
                                spacing: Style.space(6)
                                RowLayout {
                                    width: parent.width
                                    Label { text: allowance.modelData.label; Layout.fillWidth: true }
                                    Label { text: allowance.modelData.value; font.bold: true }
                                }
                                Rectangle {
                                    width: parent.width
                                    height: Style.space(5)
                                    radius: height / 2
                                    color: Qt.alpha(root.fg, 0.12)
                                    Rectangle {
                                        width: parent.width * allowance.modelData.fill / 100
                                        height: parent.height
                                        radius: parent.radius
                                        color: Color.accent
                                    }
                                }
                            }
                        }
                    }
                    Label { text: "Plan " + root.val("plan") + " · Observed " + root.val("observed") }
                    Label {
                        visible: !!root.view.note
                        text: root.view.note || ""
                        color: root.muted
                        width: parent.width
                        wrapMode: Text.WordWrap
                        font.pixelSize: Style.font.body - 2
                    }
                    Column {
                        width: parent.width
                        spacing: Style.space(8)
                        RowLayout {
                            width: parent.width
                            Label { text: root.view.month || ""; font.bold: true; Layout.fillWidth: true }
                            Label { text: "P plan · O observed"; font.pixelSize: Style.font.body - 2; color: root.muted }
                        }
                        Grid {
                            width: parent.width
                            columns: 7
                            Repeater {
                                model: ["M", "T", "W", "T", "F", "S", "S"]
                                Label {
                                    required property string modelData
                                    width: parent.width / 7
                                    text: modelData
                                    horizontalAlignment: Text.AlignHCenter
                                    color: root.muted
                                    font.pixelSize: Style.font.body - 2
                                }
                            }
                        }
                        Grid {
                            width: parent.width
                            columns: 7
                            rowSpacing: Style.space(3)
                            Repeater {
                                model: root.view.cells || []
                                Rectangle {
                                    id: cell
                                    required property var modelData
                                    width: parent.width / 7
                                    height: Style.space(58)
                                    color: modelData.active ? Qt.alpha(Color.accent, 0.28) : modelData.highlighted ? Qt.alpha(Color.accent, 0.12) : "transparent"
                                    border.width: modelData.active ? 1 : 0
                                    border.color: Color.accent
                                    Column {
                                        anchors.centerIn: parent
                                        spacing: Style.space(3)
                                        Label {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: cell.modelData.day
                                            color: cell.modelData.muted ? root.muted : root.fg
                                            font.bold: cell.modelData.active
                                        }
                                        Label {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            visible: cell.modelData.highlighted
                                            text: cell.modelData.entries.length ? "P " + cell.modelData.entries[0].plan : ""
                                            color: cell.modelData.entries.length && cell.modelData.entries[0].future ? root.muted : root.fg
                                            font.pixelSize: Style.font.body - 3
                                        }
                                        Label {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            visible: cell.modelData.highlighted
                                            text: cell.modelData.entries.length ? "O " + cell.modelData.entries[0].observed : ""
                                            color: root.muted
                                            font.pixelSize: Style.font.body - 3
                                        }
                                    }
                                    MouseArea { id: hover; anchors.fill: parent; hoverEnabled: true }
                                    ToolTip.visible: hover.containsMouse && modelData.highlighted
                                    ToolTip.delay: 550
                                    ToolTip.text: modelData.detail
                                }
                            }
                        }
                    }
                    RowLayout {
                        width: parent.width
                        Label { text: "Resets available"; Layout.fillWidth: true }
                        Label { text: root.val("credits"); font.bold: true }
                    }
                    Label {
                        width: parent.width
                        text: root.val("status")
                        color: root.muted
                        font.pixelSize: Style.font.body - 2
                        wrapMode: Text.WordWrap
                        MouseArea { id: statusHover; anchors.fill: parent; hoverEnabled: true }
                        ToolTip.visible: statusHover.containsMouse
                        ToolTip.delay: 550
                        ToolTip.text: root.view.detail || ""
                    }
                }
            }
        }
    }
}
