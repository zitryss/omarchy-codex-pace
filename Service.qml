import QtQuick
import Quickshell.Io

Item {
    id: root
    property var shell: null
    property var manifest: null
    property string omarchyPath: ""
    property var liveView: ({status: "Reading Codex quota…", cells: []})
    property var previewView: null
    readonly property var view: previewView || liveView
    property bool stopping: false
    function refresh() { if (worker.running) worker.write("refresh\n") }
    Process {
        id: worker
        command: ["python3", "-B", decodeURIComponent(Qt.resolvedUrl("pace.py").toString().replace(/^file:\/\//, "")), "watch"]
        stdinEnabled: true
        running: true
        stdout: SplitParser {
            onRead: line => {
                try { root.liveView = JSON.parse(line) } catch (e) { root.liveView = {status: "Invalid collector output", cells: []} }
            }
        }
        onExited: {
            root.liveView = Object.assign({}, root.liveView, {status: "Collector stopped · last reading retained"})
            if (!root.stopping) restart.restart()
        }
    }
    // Explicit read-only test surface; synthetic data never enters the live ledger.
    function clearPreview() { previewView = null; previewExpiry.stop() }
    function preview(name) {
        if (["normal", "debt", "zero", "correction", "stale", "expired", "auth", "year", "dst"].indexOf(name) < 0)
            return "unknown fixture"
        if (previewWorker.running) return "busy"
        previewWorker.command = ["python3", "-B", decodeURIComponent(Qt.resolvedUrl("tests/preview.py").toString().replace(/^file:\/\//, "")), name]
        previewWorker.running = true
        return "ok"
    }
    Process {
        id: previewWorker
        stdout: SplitParser {
            onRead: line => {
                try { root.previewView = JSON.parse(line); previewExpiry.restart() } catch (e) { root.previewView = null }
            }
        }
    }
    Timer { id: previewExpiry; interval: 60000; onTriggered: root.previewView = null }
    Timer { id: restart; interval: 10000; onTriggered: worker.running = true }
    Component.onDestruction: { stopping = true; worker.running = false }
}
