import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import qs.Ui

// LAW 17: everything on one screen. Only the session list scrolls, in place, in its own box.
Panel {
  id: panel
  moduleName: "nixfred.larrylamp"
  // IPC target so scripts can open it: omarchy-shell nixfred.larrylamp toggle
  ipcTarget: "nixfred.larrylamp"

  required property var widget
  readonly property var svc: widget.svc
  readonly property var st: svc ? svc.st : null

  readonly property color foreground: widget.bar ? widget.bar.foreground : Color.foreground
  readonly property color dim: Util.alpha(foreground, 0.62)
  readonly property color faint: Util.alpha(foreground, 0.10)
  readonly property string fontFamily: widget.bar ? widget.bar.fontFamily : Style.font.family
  readonly property string mono: "monospace"
  readonly property int panelWidth: Style.space(620)
  readonly property int rowH: Style.space(30)
  readonly property int maxRows: 6
  // Fixed status colours (themes may map red/urgent to green)
  readonly property var stateColor: ({ wait: "#f5a623", fail: "#ff4d5e", think: "#a855ff", ship: "#2dff9a", idle: "#5b7fa8" })
  readonly property var stateName: ({ wait: "needs you", fail: "failed", think: "thinking", ship: "done", idle: "idle" })

  function ago(s) { return s < 60 ? s + "s" : Math.round(s / 60) + "m" }
  function ask() {
    var t = askField.text.trim()
    if (!t || !svc) return
    svc.act("ask", t)
    askField.text = ""
    sent.text = "asked: " + t
  }

  component LampButton: Rectangle {
    id: b
    property string label: ""
    property string tip: ""
    signal clicked()
    Layout.fillWidth: true
    implicitHeight: Style.space(30)
    radius: Style.space(4)
    color: ma.containsMouse ? Util.alpha(Color.accent, 0.18) : panel.faint
    border.width: 1
    border.color: ma.containsMouse ? Color.accent : Util.alpha(panel.foreground, 0.18)
    Text {
      anchors.centerIn: parent
      text: b.label
      color: panel.foreground
      font.family: panel.fontFamily
      font.pixelSize: Style.font.bodySmall
    }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; onClicked: b.clicked() }
    PanelToolTip { visible: ma.containsMouse && b.tip !== ""; text: b.tip }
  }

  KeyboardPanel {
    id: kpanel
    anchorItem: panel.widget.anchorItem
    owner: panel.widget
    bar: panel.widget.bar
    open: panel.opened
    focusTarget: askField
    contentWidth: kpanel.fittedContentWidth(panel.panelWidth)
    contentHeight: kpanel.fittedContentHeight(content.implicitHeight, Style.space(640))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: panel.widget.close()

      ColumnLayout {
        id: content
        width: parent.width
        spacing: Style.space(10)

        // ------------------------------------------------------------ header
        RowLayout {
          Layout.fillWidth: true
          spacing: Style.space(10)
          Rectangle {
            width: Style.space(14); height: width; radius: width / 2
            color: "transparent"; border.width: 3; border.color: panel.widget.ringColor
          }
          Text {
            text: "LARRY LAMP"
            color: panel.foreground
            font.family: panel.fontFamily
            font.pixelSize: Style.font.subtitle
            font.bold: true
            font.letterSpacing: 2
          }
          Text {
            text: !panel.widget.online ? "offline" : (panel.st.locked ? "away" : (panel.st.led.hex + "  " + (panel.st.led.effect || "solid")))
            color: panel.dim
            font.family: panel.mono
            font.pixelSize: Style.font.bodySmall
          }
          Item { Layout.fillWidth: true }
          Rectangle {
            visible: panel.widget.online && panel.st.theme !== ""
            implicitWidth: themeTxt.implicitWidth + Style.space(16)
            implicitHeight: Style.space(22)
            radius: height / 2
            color: "transparent"; border.width: 1; border.color: Color.accent
            Text {
              id: themeTxt
              anchors.centerIn: parent
              text: "◆ " + String(panel.st && panel.st.theme ? panel.st.theme : "").replace(/-/g, " ")
              color: panel.foreground
              font.family: panel.mono
              font.pixelSize: Style.font.bodySmall
            }
          }
        }

        // ----------------------------------------------------- ask Larry
        RowLayout {
          Layout.fillWidth: true
          spacing: Style.space(8)
          TextField {
            id: askField
            Layout.fillWidth: true
            placeholderText: "Talk to Larry... (Enter)"
            foreground: panel.foreground
            font.family: panel.fontFamily
            Keys.onReturnPressed: panel.ask()
            Keys.onEnterPressed: panel.ask()
            Keys.onEscapePressed: panel.widget.close()
          }
          LampButton { Layout.fillWidth: false; implicitWidth: Style.space(96); label: "✦ ask"; tip: "Larry answers through the lamp (Claude Code on gus, read-only)"; onClicked: panel.ask() }
        }
        Text { id: sent; visible: text !== ""; text: ""; color: panel.dim; font.family: panel.mono; font.pixelSize: Style.font.bodySmall - 1; elide: Text.ElideRight; Layout.fillWidth: true }

        // --------------------------------------------------- Larry said
        Rectangle {
          Layout.fillWidth: true
          implicitHeight: saidTxt.implicitHeight + Style.space(16)
          radius: Style.space(4)
          color: Util.alpha(Color.accent, 0.08)
          border.width: 1
          border.color: Util.alpha(Color.accent, 0.5)
          Text {
            id: saidTxt
            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: Style.space(10) }
            text: panel.st && panel.st.said ? "Larry: " + panel.st.said : "Larry hasn't said anything yet."
            wrapMode: Text.WordWrap
            maximumLineCount: 4
            elide: Text.ElideRight
            color: panel.foreground
            font.family: panel.fontFamily
            font.pixelSize: Style.font.body
          }
        }

        // ------------------------------------------------------ sessions
        Text {
          text: "SESSIONS  " + (panel.st ? panel.st.sessions.length : 0)
          color: panel.dim
          font.family: panel.mono
          font.pixelSize: Style.font.bodySmall
          font.letterSpacing: 2
        }
        ListView {
          id: list
          Layout.fillWidth: true
          Layout.preferredHeight: Math.max(1, Math.min(count, panel.maxRows)) * (panel.rowH + spacing)
          clip: true
          spacing: Style.space(2)
          interactive: count > panel.maxRows
          boundsBehavior: Flickable.StopAtBounds
          model: panel.st ? panel.st.sessions : []
          delegate: RowLayout {
            required property var modelData
            width: ListView.view.width
            height: panel.rowH
            spacing: Style.space(8)
            Rectangle {
              width: Style.space(10); height: width; radius: width / 2; border.width: 0
              color: panel.stateColor[modelData.state] || panel.dim
            }
            Text {
              Layout.fillWidth: true
              text: modelData.project
              elide: Text.ElideRight
              color: modelData.state === "wait" ? panel.stateColor.wait : panel.foreground
              font.bold: modelData.state === "wait"
              font.family: panel.fontFamily
              font.pixelSize: Style.font.body
            }
            Text { text: modelData.host; color: panel.dim; font.family: panel.mono; font.pixelSize: Style.font.bodySmall }
            Text {
              Layout.preferredWidth: Style.space(120)
              horizontalAlignment: Text.AlignRight
              text: (panel.stateName[modelData.state] || modelData.state) + " · " + panel.ago(modelData.age)
              color: panel.dim
              font.family: panel.mono
              font.pixelSize: Style.font.bodySmall
            }
          }
          Text {
            visible: list.count === 0
            anchors.centerIn: parent
            text: "No Claude sessions right now."
            color: panel.dim
            font.family: panel.fontFamily
            font.pixelSize: Style.font.bodySmall
          }
        }

        // ------------------------------------------------------ controls
        GridLayout {
          Layout.fillWidth: true
          columns: 4
          columnSpacing: Style.space(6)
          rowSpacing: Style.space(6)
          LampButton { label: "nod"; tip: "The lamp nods"; onClicked: panel.svc.act("nod") }
          LampButton { label: "look at me"; tip: "Turn the head to you"; onClicked: panel.svc.act("look") }
          LampButton { label: "theme light"; tip: "Ring to the current Omarchy theme accent"; onClicked: panel.svc.act("theme-light") }
          LampButton { label: "wake"; tip: "Greeting motion"; onClicked: panel.svc.act("wake") }
          LampButton { label: "sleep"; tip: "Sleepy motion and light off"; onClicked: panel.svc.act("sleep") }
          LampButton {
            label: panel.st && panel.st.hooks ? "sessions: on" : "sessions: muted"
            tip: "Whether this machine's Claude Code sessions drive the lamp (~/.config/larry-lamp/disabled)"
            onClicked: panel.svc.act(panel.st && panel.st.hooks ? "hooks-off" : "hooks-on")
          }
          LampButton {
            Layout.columnSpan: 2
            label: "open console"
            tip: panel.st && panel.st.console ? panel.st.console : ""
            onClicked: { if (panel.st) Quickshell.execDetached(["xdg-open", panel.st.console]); panel.widget.close() }
          }
        }

        Text {
          Layout.fillWidth: true
          text: "Enter asks Larry  |  Esc closes  |  omarchy-shell nixfred.larrylamp toggle"
          color: panel.dim
          horizontalAlignment: Text.AlignRight
          font.family: panel.mono
          font.pixelSize: Style.font.bodySmall - 1
        }
      }
    }
  }
}
