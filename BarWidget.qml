import QtQuick
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui

// A ring lit in the lamp's real LED colour, breathing when the lamp breathes.
// Amber badge with a count when a Claude session is waiting on Fred.
BarWidget {
  id: root
  moduleName: "nixfred.larrylamp"
  property var anchorItem: button

  readonly property var svc: bar && bar.shell ? bar.shell.serviceFor(moduleName) : null
  readonly property var st: svc ? svc.st : null
  readonly property bool online: !!(svc && svc.ready && st && st.online)
  readonly property color foreground: bar ? bar.foreground : Commons.Color.foreground
  // Fixed amber: some themes map urgent colours to green, so "needs you" never derives from the palette.
  readonly property color waitColor: "#f5a623"
  readonly property int waiting: st ? (st.waiting || 0) : 0
  readonly property color ringColor: !online ? Util.alpha(foreground, 0.3)
    : (st.led && st.led.on && st.led.hex && st.led.hex !== "#000000") ? st.led.hex : Util.alpha(foreground, 0.35)
  readonly property bool breathing: online && st.led && (st.led.effect === "breathing" || st.led.effect === "pulse")

  implicitWidth: vertical ? barSize : Style.space(waiting > 0 ? 40 : 24)
  implicitHeight: vertical ? Style.space(waiting > 0 ? 40 : 24) : barSize

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""
    labelVisible: false
    hasVisualContent: true
    active: false
    useActiveColor: false
    tooltipText: {
      if (!root.online) return root.st && root.st.broker
        ? "Larry Lamp: the lamp is not answering (broker is up)" + (root.waiting > 0 ? "\n" + root.waiting + " session" + (root.waiting > 1 ? "s" : "") + " need you" : "")
        : "Larry Lamp: offline (neither the lamp nor its broker answers)"
      var s = "Larry Lamp  " + (root.st.theme || "") + (root.st.locked ? "  (away)" : "")
      if (root.waiting > 0) s += "\n" + root.waiting + " session" + (root.waiting > 1 ? "s" : "") + " need you"
      if (root.st.said) s += "\nLarry: " + root.st.said
      return s
    }

    Row {
      anchors.centerIn: parent
      spacing: Style.space(4)

      Item {
        width: Style.space(15); height: width
        anchors.verticalCenter: parent.verticalCenter
        Rectangle {  // the lamp's ring
          id: ring
          anchors.centerIn: parent
          width: parent.width; height: width; radius: width / 2
          color: "transparent"; border.width: Math.max(2, width * 0.2); border.color: root.ringColor
          Behavior on border.color { ColorAnimation { duration: 400 } }
          SequentialAnimation on opacity {
            running: root.breathing; loops: Animation.Infinite
            NumberAnimation { to: 0.45; duration: 1400; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.0; duration: 1400; easing.type: Easing.InOutSine }
            // An Animation has no parent property: the old "parent.opacity" resolved outside the ring,
            // so when the lamp stopped breathing mid-fade the ring stayed dimmed at whatever opacity it had.
            onRunningChanged: if (!running) ring.opacity = 1
          }
        }
        Rectangle {  // the head's lens
          anchors.centerIn: parent
          width: parent.width * 0.3; height: width; radius: width / 2; border.width: 0
          color: root.online ? root.foreground : Util.alpha(root.foreground, 0.3)
        }
      }

      Rectangle {
        visible: root.waiting > 0
        anchors.verticalCenter: parent.verticalCenter
        width: Style.space(14); height: width; radius: width / 2; border.width: 0
        color: root.waitColor
        Text {
          anchors.centerIn: parent
          text: String(root.waiting)
          color: "#111111"
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.bodySmall
          font.bold: true
        }
      }
    }

    onPressed: function(code) {
      if (root.bar) root.bar.hideTooltip(root)
      root.toggle()
    }
  }

  readonly property bool opened: panel.opened
  function open() { panel.controller.show() }
  function close() { panel.controller.hide() }
  function toggle() { opened ? close() : open() }
  function closeForPopoutSwitch() { close() }
  readonly property bool popoutSwitchClosing: false

  LampPanel {
    id: panel
    widget: root
  }
}
