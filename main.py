import sys
import threading
import keyboard
import requests

from PyQt5.QtWidgets import (QApplication, QTextEdit, QWidget, QVBoxLayout)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QPoint
from PyQt5.QtGui import QCursor

# Gemini API Configuration
GEMINI_API_KEY = "AIzaSyAF035gfgxDKBc3nzflcCcGGmHfLxkph5A"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-preview-03-25:generateContent?key={GEMINI_API_KEY}"

class PopupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.tab_handler = None

    def initUI(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(400, 150)
        self.setWindowOpacity(0.8)
        self.setStyleSheet("background-color: white; border: none; padding: 0px;")

        layout = QVBoxLayout()
        self.input_field = DragDropTextEdit()
        layout.addWidget(self.input_field)
        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        cursor_position = QCursor.pos()
        self.move(cursor_position - QPoint(200, 75))

        if not self.tab_handler:
            self.tab_handler = keyboard.add_hotkey('tab', self.close)

    def closeEvent(self, event):
        if self.tab_handler:
            keyboard.remove_hotkey(self.tab_handler)
            self.tab_handler = None
        super().closeEvent(event)

class TrayApp(QObject):
    response_received = pyqtSignal(str)
    clear_requested = pyqtSignal()
    timer_stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.popup = PopupWindow()
        self.clear_timer = None

        # Hotkeys
        keyboard.add_hotkey('alt+q', self.show_popup)
        keyboard.add_hotkey('alt+x', self.process_input)
        keyboard.add_hotkey('alt+c', self.trigger_clear)

        # Signal connections
        self.response_received.connect(self.handle_response)
        self.clear_requested.connect(self.clear_input)
        self.timer_stop_requested.connect(self.stop_timer)

    def process_input(self):
        text = self.popup.input_field.toPlainText().strip()
        if text:
            threading.Thread(target=self.get_gemini_response, args=(text,)).start()

    def get_gemini_response(self, text):
        try:
            headers = {'Content-Type': 'application/json'}
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": text + "give the correct code in c langugage , without any explanation, no explanation needed, just the code.there should no commments and no markdown"
                            }
                        ]
                    }
                ]
            }

            response = requests.post(API_URL, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()
            if 'candidates' in result and result['candidates']:
                response_text = result['candidates'][0]['content']['parts'][0]['text']
            else:
                response_text = "No response from API"

            self.response_received.emit(response_text)

        except Exception as e:
            self.response_received.emit(f"Error: {str(e)}")

    def handle_response(self, text):
        self.timer_stop_requested.emit()

        # Show complete response without trimming
        processed_text = text
        self.popup.input_field.setPlainText(processed_text)

        # Copy full response to clipboard
        QApplication.clipboard().setText(text)

        # Create new timer in main thread
        self.clear_timer = QTimer()
        self.clear_timer.setSingleShot(True)
        self.clear_timer.timeout.connect(self.clear_input)
        self.clear_timer.start(80000000)

    def trigger_clear(self):
        self.timer_stop_requested.emit()
        self.clear_requested.emit()

    def stop_timer(self):
        if self.clear_timer:
            self.clear_timer.stop()
            self.clear_timer = None

    def clear_input(self):
        self.popup.input_field.clear()
        self.clear_timer = None

    def show_popup(self):
        QTimer.singleShot(0, self.popup.show)

    def on_exit(self):
        keyboard.unhook_all()
        QApplication.quit()

class DragDropTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText("Drag text here or type...")
        self.setStyleSheet("""
            QTextEdit {
                background-color: white;
                font-size: 14px;
                border: 1px solid #ccc;
                padding: 5px;
                outline: none;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.setText(event.mimeData().text())
        event.acceptProposedAction()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray = TrayApp()
    sys.exit(app.exec_())