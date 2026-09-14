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
    function metricStatus() {
        let rows = []
        for (let i = 0; i < metrics.count; i++) {
            let row = metrics.itemAt(i)
            if (row) rows.push({label: row.label, reading: row.reading, fraction: row.fraction, color: String(row.fillColor), green: String(row.green), gray: String(row.gray), red: String(row.red)})
        }
        return rows
    }
    onOpenedChanged: if (opened && service) service.refreshIfStale()

    // IPC belongs to the visual scene; one distinct endpoint per monitor.
    IpcHandler {
        enabled: !!root.QsWindow.window && !!root.QsWindow.window.screen
        target: root.moduleName + "." + (root.QsWindow.window?.screen?.name || "pending")
        function status(): string { return JSON.stringify({opened: root.opened, scrollY: flick.contentY, contentHeight: flick.contentHeight, viewportHeight: flick.height, scrollable: flick.interactive, metrics: root.metricStatus(), refreshFocused: refreshButton.activeFocus, refreshPosition: refreshButton.mapToGlobal(refreshButton.width/2, refreshButton.height/2), view: root.view}) }
        function open(): void { root.open() }
        function close(): void { root.close() }
        function refresh(): void { if (root.service) root.service.refresh() }
        function preview(name: string): string { return root.service ? root.service.preview(name) : "unavailable" }
        function palette(fraction: real, clock: bool, light: bool): string {
            let sample = metricProbe.createObject(root, {fraction: fraction, countdown: clock, background: light ? "#fafafa" : "#191b25"})
            let result = JSON.stringify({color: String(sample.fillColor), green: String(sample.green), red: String(sample.red), gray: String(sample.gray)})
            sample.destroy()
            return result
        }
        function clearPreview(): void { if (root.service) root.service.clearPreview() }
    }

    // Read-only palette probe for native-host tests; never changes the desktop theme.
    Component { id: metricProbe; MetricRow { label: "TEST palette"; reading: "TEST"; visible: false } }
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
        contentHeight: Math.ceil(fittedContentHeight(Math.ceil(content.implicitHeight), Style.space(720)))
        PanelKeyCatcher {
            id: keys
            anchors.fill: parent
            onCloseRequested: root.close()
            onTabRequested: direction => {
                if (!refreshButton.activeFocus) {
                    flick.contentY = Math.max(0, flick.contentHeight - flick.height)
                    refreshButton.forceActiveFocus()
                }
                else root.switchPanel(direction)
            }
            onActivateRequested: { if (root.service) root.service.refresh() }
            onMoveRequested: (dx, dy) => {
                flick.contentY = Math.max(0, Math.min(flick.contentHeight - flick.height, flick.contentY + dy * Style.space(45)))
            }
            onTextKey: text => { if ((text === "r" || text === "R") && root.service) root.service.refresh() }
            Flickable {
                id: flick
                anchors.fill: parent
                contentHeight: Math.ceil(content.implicitHeight)
                contentWidth: width
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentHeight > height
                onInteractiveChanged: if (!interactive) contentY = 0
                Column {
                    id: content
                    width: parent.width
                    spacing: Style.space(16)
                    Label { text: root.view.fixture ? "Codex Pace · TEST FIXTURE: " + root.view.fixture : "Codex Pace"; font.bold: true; font.pixelSize: Style.font.body + 2 }
                    Column {
                        width: parent.width
                        spacing: Style.space(12)
                        Repeater {
                            id: metrics
                            model: [
                                {label: "Today's quota left", reading: root.pct("daily"), fraction: root.val("daily") === "—" ? null : root.view.dailyFill / 100, clock: false, tip: root.view.planBasis || ""},
                                {label: "Bucket resets in", reading: root.val("countdown"), fraction: root.view.bucketFill ?? null, clock: true, tip: "Time until the active provider-aligned planning bucket ends."},
                                {label: "Weekly quota left", reading: root.pct("weekly"), fraction: root.val("weekly") === "—" ? null : root.view.weeklyFill / 100, clock: false, tip: "Remaining quota reported by Codex."},
                                {label: "Weekly resets in", reading: root.val("weeklyCountdown"), fraction: root.view.weeklyResetFill ?? null, clock: true, tip: "Time until the provider's actual weekly quota reset."}
                            ]
                            MetricRow {
                                required property var modelData
                                width: parent.width
                                label: modelData.label
                                reading: modelData.reading
                                fraction: modelData.fraction
                                countdown: modelData.clock
                                explanation: modelData.tip
                            }
                        }
                    }
                    Label {
                        text: "Plan " + root.val("plan") + " · Used " + root.val("used") + (root.view.usedEstimated ? "*" : "")
                        MouseArea { id: planHover; anchors.fill: parent; hoverEnabled: true }
                        ToolTip.visible: planHover.containsMouse && !!root.view.planBasis
                        ToolTip.text: (root.view.planBasis || "") + "\n" + (root.view.usedBasis || "")
                        Accessible.name: "Plan " + root.val("plan") + "; Used " + root.val("used") + (root.view.usedEstimated ? " estimated" : "")
                        Accessible.description: (root.view.planBasis || "") + " " + (root.view.usedBasis || "")
                    }
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
                            Label { text: "P plan · U used" + (root.view.hasEstimates ? " · * estimated" : ""); font.pixelSize: Style.font.body - 2; color: root.muted }
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
                                    color: modelData.active ? "#3d5275" : modelData.highlighted ? Qt.alpha(Color.accent, 0.12) : "transparent"
                                    border.width: modelData.today ? 3 : 0
                                    border.color: "#a33b4d"
                                    Accessible.name: modelData.date
                                    Accessible.description: modelData.detail
                                    Column {
                                        anchors.centerIn: parent
                                        spacing: Style.space(3)
                                        Label {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: cell.modelData.day
                                            color: cell.modelData.active ? root.fg : cell.modelData.muted ? root.muted : root.fg
                                            font.bold: cell.modelData.active
                                        }
                                        Label {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            visible: cell.modelData.entries.length > 0
                                            text: cell.modelData.entries.length ? "P " + cell.modelData.entries[0].plan : ""
                                            color: cell.modelData.active ? root.fg : cell.modelData.entries.length && cell.modelData.entries[0].future ? root.muted : root.fg
                                            font.pixelSize: Style.font.body - 3
                                        }
                                        Label {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            visible: cell.modelData.entries.length > 0
                                            text: cell.modelData.entries.length ? "U " + cell.modelData.entries[0].used + (cell.modelData.entries[0].usedEstimated ? "*" : "") : ""
                                            color: cell.modelData.active ? Qt.alpha(root.fg, 0.85) : root.muted
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
                    RowLayout {
                        width: parent.width
                        Label {
                            Layout.fillWidth: true
                            text: root.val("status")
                            color: root.muted
                            font.pixelSize: Style.font.body - 2
                            wrapMode: Text.WordWrap
                            MouseArea { id: statusHover; anchors.fill: parent; hoverEnabled: true }
                            ToolTip.visible: statusHover.containsMouse
                            ToolTip.delay: 550
                            ToolTip.text: root.view.detail || ""
                        }
                        PanelActionButton {
                            id: refreshButton
                            iconText: "󰁪"
                            tooltipText: root.view.pending ? "Refreshing…" : "Refresh"
                            Accessible.name: "Refresh"
                            Accessible.role: Accessible.Button
                            Accessible.description: root.view.pending ? "Refreshing quota statistics" : "Refresh quota statistics"
                            focusable: true
                            enabled: !root.view.pending
                            opacity: root.view.pending ? 0.45 : 1
                            onClicked: if (root.service) root.service.refresh()
                        }
                    }
                }
            }
        }
    }
}
