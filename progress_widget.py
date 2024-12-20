from PyQt5.QtWidgets import QWidget, QVBoxLayout, QProgressBar
from PyQt5.QtCore import QTimer

class ProgressWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Create progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
        
        # Initialize variables
        self.current_value = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        
    def start_progress(self, duration_ms):
        self.current_value = 0
        self.progress_bar.setValue(0)
        
        # Calculate timer interval for 100 steps
        interval = int(duration_ms / 100)
        
        # Ensure minimum interval of 1ms
        interval = max(1, interval)
        
        self.timer.start(interval)
        
    def update_progress(self):
        self.current_value += 1
        self.progress_bar.setValue(self.current_value)
        
        if self.current_value >= 100:
            self.timer.stop()
            self.current_value = 0