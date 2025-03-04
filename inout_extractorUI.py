# Version: 3.9 - Three-Line Quick-Insert, Wider Combos, Conditional Button Colors, with Play Option
# Filename: inout_extractorUI_multi_timestamp.py
# Date (JST): 2025-02-27 16:10

import os
import sys
import subprocess
import datetime
from functools import partial

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, QLabel,
    QListWidget, QListWidgetItem, QHBoxLayout, QComboBox, QMessageBox, QFrame,
    QScrollArea, QGridLayout
)
from PyQt5.QtGui import QFont, QIntValidator, QDesktopServices
from PyQt5.QtCore import Qt, QUrl

# Constants
OUTPUT_FOLDER = "./output"

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

class FocusComboBox(QComboBox):
    """
    A custom QComboBox that:
      - Is editable for manual entry
      - Validates numeric input within a specified range
      - Notifies the main window when focused (so quick-insert buttons know which box to update)
      - Shows a thin stroke (1px) matching its text color by default
      - Shows a thicker (2px) orange stroke on focus
    """
    def __init__(self, parent, main_window, min_val=0, max_val=59, base_color="#00FFFF"):
        super().__init__(parent)
        self.main_window = main_window
        self.min_val = min_val
        self.max_val = max_val
        self.base_color = base_color  # color for text & default border

        # Allow manual editing
        self.setEditable(True)
        # Limit manual input to the valid numeric range
        self.setValidator(QIntValidator(self.min_val, self.max_val, self))

        # Base stylesheet:
        #  - 1px border of base_color
        #  - 2px orange border on focus
        self.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {self.base_color};
            }}
            QComboBox:focus {{
                border: 2px solid #FFA500;
            }}
        """)

    def focusInEvent(self, e):
        self.main_window.current_combo = self  # Mark this combo as "active"
        super().focusInEvent(e)

class VideoExtractor(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Multi-Video In-Out Extractor")
        self.setGeometry(100, 100, 900, 600)
        self.setStyleSheet("background-color: #121212; color: white;")

        self.video_list = []  # Store video file paths
        self.current_combo = None  # Track which combo box is currently focused

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Header Label
        header = QLabel("Multi-Video In-Out Extractor")
        header.setFont(QFont("Arial", 20, QFont.Bold))
        header.setStyleSheet("color: #E0E0E0;")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # Quick Insert Bar (three lines of 0-59)
        quick_insert_area = self.create_quick_insert_bar()
        main_layout.addWidget(quick_insert_area)

        # Video List
        self.video_list_widget = QListWidget()
        self.video_list_widget.setStyleSheet(
            "background-color: #1e1e1e; color: white; border: 1px solid #333;"
        )
        main_layout.addWidget(self.video_list_widget)

        # Bottom Buttons Layout
        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("Add Videos")
        self.select_btn.setStyleSheet(
            "background-color: #1f1f1f; color: white; padding: 10px; border-radius: 5px; font-size: 16px;"
        )
        self.select_btn.clicked.connect(self.add_videos)
        btn_layout.addWidget(self.select_btn)

        self.extract_all_btn = QPushButton("Extract All Videos")
        self.extract_all_btn.setStyleSheet(
            "background-color: #4caf50; color: white; font-weight: bold; padding: 10px; border-radius: 5px; font-size: 16px;"
        )
        self.extract_all_btn.clicked.connect(self.extract_all_videos)
        btn_layout.addWidget(self.extract_all_btn)

        main_layout.addLayout(btn_layout)

        # 1:3 ratio for quick-insert area vs. video list
        main_layout.setStretchFactor(quick_insert_area, 1)
        main_layout.setStretchFactor(self.video_list_widget, 3)

        self.setLayout(main_layout)

    def create_quick_insert_bar(self):
        """
        Creates a scrollable area with 60 buttons (0-59),
        laid out in 3 rows (each row = 20 buttons).
        0,1,2 => cyan text (#00FFFF); others => magenta (#FF00FF).
        """
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet("border: none;")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        container = QWidget()
        grid_layout = QGridLayout(container)
        grid_layout.setSpacing(6)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        for i in range(60):
            btn = QPushButton(str(i))
            btn.setFixedSize(80, 80)
            if i in [0, 1, 2]:
                text_color = "#00FFFF"  # cyan
            else:
                text_color = "#FF00FF"  # magenta
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {text_color};
                    background-color: #2a2a2a;
                    border-radius: 0;
                    font-size: 24px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #444444;
                }}
            """)
            btn.clicked.connect(partial(self.handle_quick_insert, i))
            row = i // 20
            col = i % 20
            grid_layout.addWidget(btn, row, col)

        scroll_area.setWidget(container)
        return scroll_area

    def handle_quick_insert(self, value):
        """Updates the currently focused combo box with the clicked value."""
        if self.current_combo is not None:
            self.current_combo.setCurrentText(str(value))

    def add_videos(self):
        file_dialog = QFileDialog()
        files, _ = file_dialog.getOpenFileNames(self, "Select Videos", "", "Video Files (*.mp4 *.avi *.mkv)")
        for file in files:
            if file not in self.video_list:
                self.video_list.append(file)
                self.add_video_ui(file)

    def add_video_ui(self, file_path):
        """Adds a UI block for a video with IN-OUT selectors, Extract and Play buttons."""
        video_frame = QFrame()
        video_frame.setStyleSheet("background-color: #1e1e1e; border: none; margin: 10px;")
        video_layout = QVBoxLayout()
        video_layout.setSpacing(10)

        # Video Title
        video_label = QLabel(f"📽 {os.path.basename(file_path)}")
        video_label.setFont(QFont("Arial", 14, QFont.Bold))
        video_layout.addWidget(video_label)

        # Time Selectors Layout
        time_layout = QHBoxLayout()
        time_layout.setSpacing(5)

        in_hour, in_min, in_sec = self.create_time_wheels()
        out_hour, out_min, out_sec = self.create_time_wheels()

        for widget in [in_hour, in_min, in_sec, out_hour, out_min, out_sec]:
            widget.setFixedSize(180, 60)

        in_label = QLabel("IN:")
        in_label.setFont(QFont("Arial", 18, QFont.Bold))
        in_label.setStyleSheet("color: #E0E0E0; margin-right: 5px;")
        time_layout.addWidget(in_label)
        time_layout.addWidget(in_hour)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(in_min)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(in_sec)

        time_layout.addSpacing(20)

        out_label = QLabel("OUT:")
        out_label.setFont(QFont("Arial", 18, QFont.Bold))
        out_label.setStyleSheet("color: #E0E0E0; margin-right: 5px;")
        time_layout.addWidget(out_label)
        time_layout.addWidget(out_hour)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(out_min)
        time_layout.addWidget(QLabel(":"))
        time_layout.addWidget(out_sec)

        video_layout.addLayout(time_layout)

        # Extract Button
        extract_btn = QPushButton("Extract")
        extract_btn.setStyleSheet(
            "background-color: #00FFFF; color: #000000; font-weight: bold; "
            "padding: 10px; border-radius: 5px; font-size: 16px;"
        )
        extract_btn.clicked.connect(
            lambda: self.extract_video(file_path, in_hour, in_min, in_sec, out_hour, out_min, out_sec)
        )
        video_layout.addWidget(extract_btn)
        
        # Play Button
        play_btn = QPushButton("Play")
        play_btn.setStyleSheet(
            "background-color: #32CD32; color: #000000; font-weight: bold; "
            "padding: 10px; border-radius: 5px; font-size: 16px;"
        )
        play_btn.clicked.connect(lambda: self.play_video(file_path))
        video_layout.addWidget(play_btn)

        video_frame.setLayout(video_layout)

        list_item = QListWidgetItem()
        list_item.setSizeHint(video_frame.sizeHint())
        self.video_list_widget.addItem(list_item)
        self.video_list_widget.setItemWidget(list_item, video_frame)

    def create_time_wheels(self):
        """Creates three time selector wheels (HH:MM:SS) with manual editing and focus tracking."""
        hour = FocusComboBox(self, main_window=self, min_val=0, max_val=23, base_color="#00FFFF")
        minute = FocusComboBox(self, main_window=self, min_val=0, max_val=59, base_color="#39FF14")
        second = FocusComboBox(self, main_window=self, min_val=0, max_val=59, base_color="red")

        hour.addItems([f"{i:02d}" for i in range(24)])
        minute.addItems([f"{i:02d}" for i in range(60)])
        second.addItems([f"{i:02d}" for i in range(60)])

        hour.setMaxVisibleItems(60)
        minute.setMaxVisibleItems(60)
        second.setMaxVisibleItems(60)

        hour.setStyleSheet(hour.styleSheet() + """
            QComboBox {
                background-color: #222; color: #00FFFF;
                font-size: 32px; font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #222; color: #00FFFF;
                selection-background-color: #333;
                font-size: 32px; font-weight: bold;
            }
        """)
        minute.setStyleSheet(minute.styleSheet() + """
            QComboBox {
                background-color: #222; color: #39FF14;
                font-size: 32px; font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #222; color: #39FF14;
                selection-background-color: #333;
                font-size: 32px; font-weight: bold;
            }
        """)
        second.setStyleSheet(second.styleSheet() + """
            QComboBox {
                background-color: #222; color: red;
                font-size: 32px; font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #222; color: red;
                selection-background-color: #333;
                font-size: 32px; font-weight: bold;
            }
        """)

        return hour, minute, second

    def extract_video(self, file_path, in_hour, in_min, in_sec, out_hour, out_min, out_sec):
        in_time = self.get_selected_time(in_hour, in_min, in_sec)
        out_time = self.get_selected_time(out_hour, out_min, out_sec)
        if in_time >= out_time:
            QMessageBox.warning(self, "Invalid Time", "OUT time must be greater than IN time.")
            return
        self.process_extraction(file_path, in_time, out_time)
        QMessageBox.information(self, "Done", f"Extraction completed for {os.path.basename(file_path)}!")

    def extract_all_videos(self):
        for index in range(self.video_list_widget.count()):
            item = self.video_list_widget.item(index)
            video_frame = self.video_list_widget.itemWidget(item)
            video_label = video_frame.layout().itemAt(0).widget().text().replace("📽 ", "")
            video_path = next((path for path in self.video_list if os.path.basename(path) == video_label), None)
            if not video_path:
                continue
            time_layout = video_frame.layout().itemAt(1).layout()
            in_hour, in_min, in_sec = time_layout.itemAt(1).widget(), time_layout.itemAt(3).widget(), time_layout.itemAt(5).widget()
            out_hour, out_min, out_sec = time_layout.itemAt(8).widget(), time_layout.itemAt(10).widget(), time_layout.itemAt(12).widget()
            self.extract_video(video_path, in_hour, in_min, in_sec, out_hour, out_min, out_sec)

    def get_selected_time(self, hour_combo, minute_combo, second_combo):
        def safe_int(val):
            try:
                return int(val)
            except:
                return 0
        h = safe_int(hour_combo.currentText())
        m = safe_int(minute_combo.currentText())
        s = safe_int(second_combo.currentText())
        return h * 3600 + m * 60 + s

    def process_extraction(self, input_file, start_time, end_time):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(input_file)
        output_file = os.path.join(OUTPUT_FOLDER, f"{filename}_clip_{timestamp}.mp4")
        subprocess.run(["ffmpeg", "-i", input_file, "-ss", str(start_time), "-to", str(end_time), "-c", "copy", output_file])

    def play_video(self, file_path):
        """Plays the selected video using the default video player."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoExtractor()
    window.show()
    sys.exit(app.exec_())
