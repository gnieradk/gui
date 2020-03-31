#!/usr/bin/env python3
from PyQt5 import QtWidgets, uic
from PyQt5 import QtCore, QtGui, QtWidgets

from toolsettings.toolsettings import ToolSettings
from monitor.monitor import Monitor
from settings.settings import Settings
from data_filler import DataFiller
from data_handler import DataHandler

import pyqtgraph as pg
import sys
import time


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config, esp32, *args, **kwargs):
        """
        Initializes the main window for the MVM GUI. See below for subfunction setup description.
        """

        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi('mainwindow.ui', self) # Load the .ui file

        self.config = config

        self.data_filler = DataFiller(config)
        self.esp32 = esp32

        '''
        Set up tool settings (bottom bar)

        self.toolsettings[..] are the objects that hold min, max values for a given setting as
        as the current value (displayed as a slider and as a number).
        '''
        self.toolsettings = [];
        self.toolsettings.append(self.findChild(QtWidgets.QWidget, "toolsettings_1"))
        self.toolsettings.append(self.findChild(QtWidgets.QWidget, "toolsettings_2"))
        self.toolsettings.append(self.findChild(QtWidgets.QWidget, "toolsettings_3"))

        self.toolsettings[0].setup("O<sub>2</sub> conc.", setrange=(21, 40, 100), units="%")
        self.toolsettings[1].setup("PEEP",                setrange=(0,   5, 50),  units="cmH<sub>2</sub>O")
        self.toolsettings[2].setup("Resp. Rate",          setrange=(4,  12, 100), units="b/min")

        '''
        Set up start/stop auto/min mode buttons.

        Connect each to their respective mode toggle functions.
        '''
        self.mode = 0 # 0 is stop, 1 is auto, 2 is assisted
        self.button_startauto = self.findChild(QtWidgets.QPushButton, "button_startauto")
        self.button_startman = self.findChild(QtWidgets.QPushButton, "button_startman")
        self.button_startauto.pressed.connect(self.toggle_automatic)
        self.button_startman.pressed.connect(self.toggle_assisted)

        '''
        Set up data monitor/alarms (side bar)

        self.monitors[..] are the objects that hold monitor values and thresholds for alarm min
        and max. The current value and optional stats for the monitored value (mean, max) are set
        here.
        '''
        monitor_names = {"monitor_top", "monitor_mid", "monitor_bot"};
        self.monitors = {};
        monitor_default = {
                "name": "NoName",
                "min": 0,
                "init": 50,
                "max": 100,
                "step": None,
                "units": None,
                "dec_precision": 2,
                "color": "black",
                "alarmcolor": "red"}

        for name in monitor_names:
            monitor = self.findChild(QtWidgets.QWidget, name)
            entry = config.get(name, monitor_default)
            monitor.setup(
                    entry.get("name", monitor_default["name"]),
                    setrange=(
                        entry.get("min", monitor_default["min"]),
                        entry.get("init", monitor_default["init"]),
                        entry.get("max", monitor_default["max"])),
                    units=entry.get("units", monitor_default["units"]),
                    alarmcolor=entry.get("alarmcolor", monitor_default["alarmcolor"]),
                    color=entry.get("color", monitor_default["color"]),
                    step=entry.get("step", monitor_default["step"]),
                    dec_precision=entry.get("dec_precision", monitor_default["dec_precision"]))
            self.monitors[name] = monitor
        self.data_filler.connect_monitor('monitor_top', self.monitors['monitor_top'])
        # Need to add the other monitors...which ones?


        '''
        Set up plots (PyQtPlot)

        self.plots[..] are the PyQtPlot objects.
        '''
        self.plots = [];
        self.plots.append(self.findChild(QtWidgets.QWidget, "plot_top"))
        self.plots.append(self.findChild(QtWidgets.QWidget, "plot_mid"))
        self.plots.append(self.findChild(QtWidgets.QWidget, "plot_bot"))
        self.data_filler.connect_plot('monitor_top', self.plots[0])
        self.data_filler.connect_plot('monitor_mid', self.plots[1])
        self.data_filler.connect_plot('monitor_bot', self.plots[2])

        '''
        Connect settings button to Settings overlay.
        '''
        self.settings = Settings(self)
        self.button_settings = self.findChild(QtWidgets.QPushButton, "button_settings")
        self.button_settings.pressed.connect(self.settings.show)

        '''
        Instantiate DataHandler, which will start a new
        thread to read data from the ESP32. We also connect
        the DataFiller to it, so the thread will pass the
        data directly to the DataFiller, which will
        then display them.
        '''
        self._data_h = DataHandler(config, self.esp32)
        self._data_h.connect_data_filler(self.data_filler)
        self._data_h.start_io_thread()

    def closeEvent(self, event):
        self._data_h.stop_io()

    def toggle_automatic(self):
        """
        Toggles between automatic mode (1) and stop (0).

        Changes text from "Start" to "Stop" and en/disables assisted button depending on mode.
        """
        if self.mode == 0:
            self.mode = 1
            self.button_startman.setDisabled(True)
            self.button_startauto.setDisabled(True)

            # Set timeout for being able to stop this mode
            palette = self.button_startauto.palette()
            role = self.button_startauto.backgroundRole() 
            if 'start_mode_timeout' in self.config:
                timeout = self.config['start_mode_timeout']
                # set maximum timeout
                if timeout > 3000: 
                    timeout = 3000
            else:
                timeout = 1000
            QtCore.QTimer.singleShot(timeout, lambda: ( 
                    # change button color and enable the stop button
                    self.button_startauto.setText("Stop Automatic"),
                    palette.setColor(role, QtGui.QColor("#fc6203")),
                    self.button_startauto.setPalette(palette),
                    self.button_startauto.setEnabled(True)))
        else:
            confirmation = QtWidgets.QMessageBox.warning(
                    self, 
                    '**STOPPING AUTOMATIC MODE**', 
                    "Are you sure you want to STOP AUTOMATIC MODE?", 
                    QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, 
                    QtWidgets.QMessageBox.Cancel)

            if confirmation == QtWidgets.QMessageBox.Ok:
                self.mode = 0
                self.button_startauto.setText("Start Automatic")
                self.button_startman.setEnabled(True)

                # change button color
                palette = self.button_startauto.palette()
                role = self.button_startauto.backgroundRole() 
                palette.setColor(role, QtGui.QColor("#eeeeee"))
                self.button_startauto.setPalette(palette)

    def toggle_assisted(self):
        """
        Toggles between assisted mode (2) and stop (0).

        Changes text from "Start" to "Stop" and en/disables automatic button depending on mode.
        """
        if self.mode == 0:
            self.mode = 2
            self.button_startauto.setDisabled(True)
            self.button_startman.setDisabled(True)
            
            # Set timeout for being able to stop this mode
            palette = self.button_startman.palette()
            role = self.button_startman.backgroundRole() 
            if 'start_mode_timeout' in self.config:
                timeout = self.config['start_mode_timeout']
                # set maximum timeout
                if timeout > 3000: 
                    timeout = 3000
            else:
                timeout = 1000
            QtCore.QTimer.singleShot(timeout, lambda: ( 
                    # change button color and enable the stop button
                    self.button_startman.setText("Stop Assisted"),
                    palette.setColor(role, QtGui.QColor("#fc6203")),
                    self.button_startman.setPalette(palette),
                    self.button_startman.setEnabled(True)))


        else:
            confirmation = QtWidgets.QMessageBox.warning(
                    self, 
                    '**STOPPING ASSISTED MODE**', 
                    "Are you sure you want to STOP ASSISTED MODE?", 
                    QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, 
                    QtWidgets.QMessageBox.Cancel)

            if confirmation == QtWidgets.QMessageBox.Ok:
                self.mode = 0
                self.button_startman.setText("Start Assisted")
                self.button_startauto.setEnabled(True)

                # change button color
                palette = self.button_startman.palette()
                role = self.button_startman.backgroundRole() 
                palette.setColor(role, QtGui.QColor("#eeeeee"))
                self.button_startman.setPalette(palette)
