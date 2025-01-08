import sys
import time
import numpy as np
import random
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.widgets import Cursor
import pyvisa
from collections import deque
#from progress_widget import ProgressWidget

class LoggingThread(QThread):
    data_ready = pyqtSignal(list)
    start_progress = pyqtSignal(float)  # Signal to start progress with sleep_time

    def __init__(self, n7745c, points, integration_time, time_unit, loop_delay, simulate_checkbox, parent=None):
        super().__init__(parent)
        self.n7745c = n7745c
        self.running = False
        self.points = points
        self.integration_time = integration_time
        self.time_unit = time_unit
        self.loop_delay = loop_delay
        self.simulate_checkbox = simulate_checkbox
        self.calculate_sleep_time()

        
    def calculate_sleep_time(self):
        """
        Calculate the sleep time based on the number of points, integration time, and time unit.

        This method computes the total sleep time required for data acquisition by multiplying
        the number of points by the integration time and converting the result to seconds
        based on the specified time unit.

        The calculated sleep time is stored in the `self.sleep_time` attribute.

        Parameters:
        -----------
        self : object
            The instance of the class containing the method.
            Expected to have the following attributes:
            - time_unit : str
                The unit of time for integration. Can be "US" (microseconds), "MS" (milliseconds), or "S" (seconds).
            - points : int
                The number of data points to be collected.
            - integration_time : float
                The integration time for each data point.

        Returns:
        --------
        None
            The method doesn't return a value but updates the `self.sleep_time` attribute.
        """
        if self.time_unit == "US":
            self.sleep_time = (self.points * self.integration_time) / 1_000_000  # Convert to seconds
        elif self.time_unit == "MS":
            self.sleep_time = (self.points * self.integration_time) / 1000  # Convert to seconds
        else:  # "S"
            self.sleep_time = self.points * self.integration_time


    def run(self):
        self.running = True

        if self.simulate_checkbox:
            pass
        else:
            self.n7745c.write(":SENSe2:FUNCtion:STATe LOGG,STAR")  # Enables the logging
        
        while self.running:
            data_1 = 0
            time.sleep(self.loop_delay)
            
            while data_1 == 0 and self.running:

                #data_1 = self.n7745c.query(":SENS2:FUNC:RES:IND?")
                if self.simulate_checkbox:
                    data_1 = 1
                else:
                    data_1 = self.n7745c.query("*OPC?")

            time.sleep(self.sleep_time)
            if self.running:
                # Emit signal to start progress bar with current sleep_time
                self.start_progress.emit(self.sleep_time)
                # Sleep for a short time to avoid excessive CPU usage
                if self.simulate_checkbox:
                    data = [random.randint(0, 10) for _ in range(self.points)]
                else:
                    data = self.n7745c.query_binary_values(':SENSE2:CHANnel:FUNCtion:RESult?', 'f', False)
                print(data)
                print(len(data))
                print(f"La valeur de data est toujours {data_1}")
                self.data_ready.emit(data)

        if self.simulate_checkbox:
            pass
        else:
            self.n7745c.write(":SENSe2:FUNCtion:STATe LOGG,STOP")  # Disables the logging

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.Initialize_VISA_resource()

        # Initialize data storage for the scrolling plot
        self.time_data = deque(maxlen=100)
        self.first_point_data = deque(maxlen=100)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_second_graph)
        self.update_timer.start(1)
        self.pending_data = None
        self.current_data = []

    def Initialize_VISA_resource(self):


        if self.simulateCheckbox.isChecked():
            self.n7745c = None  
        else:
            rm = pyvisa.ResourceManager()
            self.n7745c = rm.open_resource('TCPIP0::169.254.241.203::inst0::INSTR')

    def initUI(self):
        # Load the UI file
        uic.loadUi('n7745c_gui.ui', self)

        # Connect buttons
        self.startButton.clicked.connect(self.start_logging)
        self.stopButton.clicked.connect(self.stop_logging)

        # Set minimum size for the main window
        self.setMinimumSize(600, 400)
        # Set up matplotlib figures
        self.figure1, self.ax1 = plt.subplots(figsize=(5, 4))
        self.canvas1 = FigureCanvas(self.figure1)
        self.plotWidget1.setLayout(QtWidgets.QVBoxLayout())
        self.plotWidget1.layout().addWidget(self.canvas1)
        self.plotWidget1.setMinimumSize(300, 200)

        self.figure2, self.ax2 = plt.subplots(figsize=(5, 4))
        self.canvas2 = FigureCanvas(self.figure2)
        self.plotWidget2.setLayout(QtWidgets.QVBoxLayout())
        self.plotWidget2.layout().addWidget(self.canvas2)
        self.plotWidget2.setMinimumSize(300, 200)
        
    def safe_set_figure_size(self, figure, canvas):
        width = max(1, canvas.width() / self.logicalDpiX())
        height = max(1, canvas.height() / self.logicalDpiY())
        figure.set_size_inches(width, height, forward=False)
        canvas.draw()
        

    def start_logging(self):
        self.logging_started = True
        points = int(self.pointsLineEdit.text())
        integration_time = int(self.integrationTimeLineEdit.text())
        time_unit = self.timeUnitComboBox.currentText()
        loop_delay = float(self.delayLineEdit.text())

        if self.simulateCheckbox.isChecked():
            pass
        else:
            self.n7745c.write(f":SENSe2:FUNCtion:PARameter:LOGGing {points},{integration_time} {time_unit}")
        
        self.logging_thread = LoggingThread(self.n7745c, points, integration_time, time_unit, loop_delay, self.simulateCheckbox)
        self.logging_thread.data_ready.connect(self.update_plot)
        self.logging_thread.start_progress.connect(self.start_progress_bar)
        self.logging_thread.start()
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)

        # Reset the data storage for the scrolling plot
        self.time_data.clear()
        self.first_point_data.clear()
        self.update_timer.start(10)

    def start_progress_bar(self, sleep_time):
        # Convert sleep_time to milliseconds for the progress widget
        delay_ms = int(sleep_time * 1000)
        #self.progress_widget.start_progress(delay_ms)

    def stop_logging(self):
        self.logging_started = False
        self.logging_thread.running = False
        self.logging_thread.wait()
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.update_timer.stop()

    def update_plot(self, data):
        self.current_data = data
        # Update the first plot (all data points)
        self.ax1.clear()
        self.ax1.plot(data)
        self.ax1.set_title('N7745C Logging Data')
        self.ax1.set_xlabel('Sample')
        self.ax1.set_ylabel('Value')
        self.safe_set_figure_size(self.figure1, self.canvas1)

        # Store the new data point for the second graph
        self.pending_data = data[0]

    def update_second_graph(self):
        if self.pending_data is not None:
            if len(self.time_data) == 0:
                self.time_data.append(0)
            else:
                self.time_data.append(self.time_data[-1] + 1)
            self.first_point_data.append(self.pending_data)

            self.ax2.clear()
            self.ax2.plot(list(self.time_data), list(self.first_point_data))
            self.ax2.set_title('First Data Point Over Time')
            self.ax2.set_xlabel('Time')
            self.ax2.set_ylabel('Value')
            self.ax2.set_xlim(max(0, self.time_data[-1] - 100), self.time_data[-1])
            self.safe_set_figure_size(self.figure2, self.canvas2)

            self.pending_data = None

    def closeEvent(self, event):

        reply = QtWidgets.QMessageBox.question(self, 'Message',
        "Are you sure you want to quit?", QtWidgets.QMessageBox.Yes | 
        QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            if hasattr(self, 'logging_started') and self.logging_started:
                self.stop_logging()
            event.accept()
        else:
            event.ignore()

        if self.simulateCheckbox.isChecked():
            pass
        else:
            self.n7745c.close()
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.safe_set_figure_size(self.figure1, self.canvas1)
        self.safe_set_figure_size(self.figure2, self.canvas2)
            

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())