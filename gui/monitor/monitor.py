#!/usr/bin/env python3
from PyQt5 import QtWidgets, uic
from PyQt5 import QtGui
class Monitor(QtWidgets.QWidget):
    def __init__(self, name, config, *args):
        """
        Initialize the Monitor widget.

        Grabs child widgets and sets alarm facility up.

        """
        super(Monitor, self).__init__(*args)
        uic.loadUi("monitor/monitor.ui", self)
        self.config = config
        self.configname = name

        self.label_name = self.findChild(QtWidgets.QLabel, "label_name")
        self.label_value = self.findChild(QtWidgets.QLabel, "label_value")
        self.label_min = self.findChild(QtWidgets.QLabel, "label_min")
        self.label_max = self.findChild(QtWidgets.QLabel, "label_max")
        self.stats_slots = self.findChild(QtWidgets.QGridLayout, "stats_slots")
        self.frame = self.findChild(QtWidgets.QFrame, "frame")

        monitor_default = {
                "name": "NoName",
                "init": 50,
                "units": None,
                "step": 1,
                "dec_precision": 0,
                "color": "white",
                "alarmcolor": "red",
                "observable": "o2",
                "disp_type": None}
        entry = self.config['monitors'].get(name, monitor_default)

        self.entry = entry
        self.name = entry.get("name", monitor_default["name"])
        self.value = entry.get("init", monitor_default["init"])
        self.units = entry.get("units", monitor_default["units"])
        self.dec_precision = entry.get("dec_precision", monitor_default["dec_precision"])
        self.color = entry.get("color", monitor_default["color"])
        self.alarmcolor = entry.get("alarmcolor", monitor_default["alarmcolor"])
        self.step = entry.get("step", monitor_default["step"])
        self.observable = entry.get("observable", monitor_default["observable"])
        self.disp_type = entry.get("disp_type", monitor_default["disp_type"])
        self.gui_alarm = None

        self.refresh()
        self.set_alarm_state(False)
        self.update_value(self.value)
        self.update_thresholds(None, None, None, None)
        self.label_value.resizeEvent = lambda event: self.handle_resize(event)

        # Handle optional custom display type
        self.display_opts = self.findChild(QtWidgets.QStackedWidget, "display_opts")
        self.shown_widget = self.findChild(QtWidgets.QWidget, "default_text")
        if self.disp_type is not None:
            if "bar" in self.disp_type:
                self.setup_bar_disp_type()
        self.display_opts.setCurrentWidget(self.shown_widget)

        # Setup config mode
        self.config_mode = False
        self.unhighlight()

        # Handle optional stats
        # TODO: determine is stats are useful/necessary

    def setup_bar_disp_type(self):
        (text, low, high) = self.disp_type.split(" ") 
        self.shown_widget = self.findChild(QtWidgets.QWidget, "progress_bar")
        self.progress_bar = self.findChild(QtWidgets.QProgressBar, "bar_value")
        self.shown_widget.setStyleSheet(
                "QProgressBar {"
                "   background-color: rgba(0,0,0,0);"
                "   text-align: center;"
                "}"
                "QProgressBar::chunk {"
                "    background-color: #888888;"
                "}")
        if self.units is None: showformat = "%p"
        else: showformat = "%p "+ self.units
        self.progress_bar.setFormat(showformat)
        self.progress_bar.setMinimum(int(low))
        self.progress_bar.setMaximum(int(high))

    def name(self):
        '''
        Returns the configuration name 
        for this monitor
        '''
        return self.configname

    def connect_gui_alarm(self, gui_alarm):
        '''
        Stores the GuiAlarm class
        '''
        self.gui_alarm = gui_alarm

    def update_thresholds(self, alarm_min, alarm_setmin, alarm_max, alarm_setmax):
        '''
        Updates the labes showind the threshold values
        '''
        self.label_min.hide()
        self.label_max.hide()
        # if self.alarm is not None:
        print("Updating thresholds for " + self.configname)

        if alarm_min is not None:
            self.label_min.setText(str(alarm_setmin))
            self.label_min.show()

        if alarm_max is not None:
            self.label_max.setText(str(alarm_setmax))
            self.label_max.show()

    def refresh(self):
        # Handle optional units
        if self.units is not None:
            self.label_name.setText(self.name + " " + str(self.units))
        else:
            self.label_name.setText(self.name)

        self.setStyleSheet("QWidget { color: " + str(self.color) + "; }");
        self.setAutoFillBackground(True)

    def handle_resize(self, event):
        # Handle font resize
        f = self.label_value.font()
        br = QtGui.QFontMetrics(f).boundingRect(self.label_value.text())

        f.setPixelSize(max(min(self.height()-23, 50), 10))
        self.label_value.setFont(f)

    def set_alarm_state(self, isalarm):
        '''
        Sets or clears the alarm
        arguments:
        - isalarm: True is alarmed state
        '''
        if isalarm:
            color = self.alarmcolor
        else:
            color = QtGui.QColor("#000000")
            if self.gui_alarm is not None: 
                self.gui_alarm.clear_alarm(self.configname)
        palette = self.palette()
        role = self.backgroundRole()
        palette.setColor(role, QtGui.QColor(color))
        self.setPalette(palette)

    def highlight(self):
        self.frame.setStyleSheet("#frame { border: 5px solid limegreen; }");

    def unhighlight(self):
        self.frame.setStyleSheet("#frame { border: 0.5px solid white; }");

    def update_value(self, value):
        if self.step is not None:
            self.value = round(value / self.step) * self.step
        else:
            self.value = value;
        if self.disp_type is not None:
            if "bar" in self.disp_type:
                self.bar_value.setValue(self.value)
        self.label_value.setText("%.*f" % (self.dec_precision, self.value))




