import QtQuick
import Quickshell
import Quickshell.Io

// larrylamp.py prints one JSON state line per interval; this keeps the latest.
// Actions run as one-shot processes so a slow lamp never blocks the bar.
Item {
  id: root

  property var settings: ({})
  readonly property string pluginDir: decodeURIComponent(String(Qt.resolvedUrl(".")).replace(/^file:\/\/(localhost)?/, ""))
  readonly property int intervalSec: {
    var n = parseInt(String(settings && settings.intervalSec !== undefined ? settings.intervalSec : 2), 10)
    return isFinite(n) ? Math.max(1, Math.min(30, n)) : 2
  }

  property bool ready: false
  property var st: ({ online: false, led: { hex: "#000000", on: false, effect: "" }, sessions: [], top: "none", waiting: 0, said: "", hooks: true, theme: "", accent: "", locked: false, console: "" })

  function apply(line) {
    var d
    try { d = JSON.parse(line) } catch (e) { return }
    if (!d || d.led === undefined) return
    st = d
    ready = true
  }

  function act(action, text) {
    var p = actComp.createObject(root, { command: ["python3", root.pluginDir + "larrylamp.py", "act", action].concat(text ? [text] : []) })
    p.running = true
  }
  Component {
    id: actComp
    Process { onRunningChanged: if (!running) destroy() }
  }

  Process {
    id: proc
    command: ["python3", root.pluginDir + "larrylamp.py", "watch", "--interval", String(root.intervalSec)]
    running: true
    stdout: SplitParser { splitMarker: "\n"; onRead: function(line) { root.apply(line) } }
    stderr: SplitParser { splitMarker: "\n"; onRead: function(line) { console.warn("larrylamp:", line) } }
    onRunningChanged: if (!running) respawn.restart()
  }
  onIntervalSecChanged: { proc.running = false; respawn.restart() }
  Timer { id: respawn; interval: 3000; onTriggered: if (!proc.running) proc.running = true }
}
