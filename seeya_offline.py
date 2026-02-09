import sys
import os
import psutil
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QScrollArea, 
                             QProgressBar, QFrame, QGraphicsDropShadowEffect, 
                             QStackedWidget, QTextBrowser, QLineEdit, QSizePolicy, QSizeGrip)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect
from PyQt5.QtGui import QColor, QFont
import assistant_offline
# dpi scaling
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# backend

import assistant_offline as logic

class SeeyaThread(QThread):
    chat_signal = pyqtSignal(str, str)
    status_signal = pyqtSignal(str)
    glow_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.is_running = True
        self.is_mic_muted = True
        self.greeted = False

    def run(self):
        self.msleep(1000)
        if not self.greeted:
            self.chat_signal.emit("Seeya", "Seeya Online.")
            assistant_offline.speak("Seeya Online")
            self.greeted = True

        while self.is_running:
            self.glow_signal.emit(logic.is_speaking)
            
           
            if self.is_mic_muted or logic.is_speaking:
                self.msleep(100)
                continue
            text = logic.listen()
            if text:
                self.chat_signal.emit("You", text)
                self.process_command(text)
            
            self.msleep(50) 

    def process_command(self, text):
        self.chat_signal.emit("Thinking", "Thinking... 🤔")
        self.status_signal.emit("Thinking...")

        command = text.lower()
        pc_reply = logic.system_commands(command)
        
        if pc_reply:
            self.chat_signal.emit("Seeya", pc_reply)
            logic.speak(pc_reply)
        else:
            ai_reply = logic.ask_gemini(text)
            self.chat_signal.emit("Seeya", ai_reply)
            logic.speak(ai_reply)
        
        self.status_signal.emit("Listening...")

class SeeyaDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seeya AI")
        self.resize(600, 420) 
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.is_maximized_custom = False 
        self.old_geometry = None 
        self.current_thinking_widget = None

        self.init_ui()
        self.init_logic()

    def init_ui(self):
        self.shadow_box = QWidget()
        self.setCentralWidget(self.shadow_box)
        self.layout_main = QVBoxLayout(self.shadow_box)
        self.layout_main.setContentsMargins(10, 10, 10, 10)

        self.main_frame = QWidget()
        self.main_frame.setObjectName("MainFrame")
        self.main_frame.setStyleSheet("""
            QWidget#MainFrame { background-color: #0F0F0F; border-radius: 12px; border: 1px solid #333; }
            * { font-family: 'Segoe UI', sans-serif; }
        """)
        
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0,0,0,150))
        self.main_frame.setGraphicsEffect(self.shadow)
        
        self.layout_main.addWidget(self.main_frame)
        
        self.hbox = QHBoxLayout(self.main_frame)
        self.hbox.setContentsMargins(0,0,0,0)
        self.hbox.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background-color: #161616; border-top-left-radius: 12px; border-bottom-left-radius: 12px; border-right: 1px solid #222;")
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(10, 20, 10, 20)
        
        self.logo = QLabel("SEEYA AI")
        self.logo.setStyleSheet("color: cyan; font-size: 18px; font-weight: bold; letter-spacing: 1px;")
        self.logo.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.logo)
        self.sidebar_layout.addSpacing(30)
        
        self.btn_chat = self.create_nav_btn("💬 Chat", 0)
        self.btn_cmds = self.create_nav_btn("⚡ Commands", 1)
        self.sidebar_layout.addStretch()
        
        self.btn_voice = QPushButton("VOICE ON")
        self.btn_voice.setFixedHeight(30)
        self.btn_voice.setCursor(Qt.PointingHandCursor)
        self.btn_voice.clicked.connect(self.toggle_voice_output)
        self.btn_voice.setStyleSheet("background:#7E57C2; color:white; border-radius:8px; font-weight:bold; font-size: 12px;")
        self.sidebar_layout.addWidget(self.btn_voice)

        self.sidebar_layout.addSpacing(10)
        self.btn_mic = QPushButton("MIC OFF")
        self.btn_mic.setFixedHeight(30)
        self.btn_mic.setCursor(Qt.PointingHandCursor)
        self.btn_mic.clicked.connect(self.toggle_mic_input)
        self.btn_mic.setStyleSheet("background:#222; color:#FF5252; border:1px solid #FF5252; border-radius:8px; font-weight:bold; font-size: 12px;")
        self.sidebar_layout.addWidget(self.btn_mic)
        
        self.sidebar_layout.addSpacing(15)
        self.lbl_cpu = QLabel("CPU LOAD")
        self.lbl_cpu.setStyleSheet("color: #666; font-size: 9px; font-weight: bold;")
        self.sidebar_layout.addWidget(self.lbl_cpu)
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFixedHeight(3)
        self.cpu_bar.setTextVisible(False)
        self.cpu_bar.setStyleSheet("QProgressBar{background:#333; border-radius:1px;} QProgressBar::chunk{background:#00FFFF;}")
        self.sidebar_layout.addWidget(self.cpu_bar)
        
        self.hbox.addWidget(self.sidebar)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(15, 10, 15, 10)
        
        self.header = QHBoxLayout()
        self.lbl_status = QLabel("● MIC OFF")
        self.lbl_status.setStyleSheet("color: #FF5252; font-weight: bold; font-size: 11px;")
        
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setFixedSize(60, 28)
        self.btn_refresh.clicked.connect(self.refresh_chat)
        self.btn_refresh.setStyleSheet("background:#222; color:white; border-radius:5px;")

        self.btn_max = QPushButton("☐") 
        self.btn_max.setFixedSize(28, 28)
        self.btn_max.clicked.connect(self.toggle_maximize) 
        self.btn_max.setStyleSheet("background:#333; color:white; border-radius:5px; font-size: 12px;")

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setStyleSheet("background:#D32F2F; color:white; border-radius:5px; font-size: 12px;")

        self.header.addWidget(self.lbl_status)
        self.header.addStretch()
        self.header.addWidget(self.btn_refresh)
        self.header.addSpacing(5)
        self.header.addWidget(self.btn_max)
        self.header.addSpacing(5)
        self.header.addWidget(self.btn_close)
        
        self.content_layout.addLayout(self.header)

        self.pages = QStackedWidget()
        
        self.page_chat = QWidget()
        self.chat_vbox = QVBoxLayout(self.page_chat)
        self.chat_vbox.setContentsMargins(0,0,0,0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:transparent; border:none;")
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.chat_container = QWidget()
        self.msg_layout = QVBoxLayout(self.chat_container)
        self.msg_layout.setSpacing(8) 
        self.msg_layout.setAlignment(Qt.AlignTop) 
        
        self.scroll.setWidget(self.chat_container)
        self.chat_vbox.addWidget(self.scroll)
        
        self.input_hbox = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Speak or Type Command...")
        self.input_box.setFixedHeight(40)
        self.input_box.setStyleSheet("background-color: #222; color: #fff; border-radius: 20px; padding: 0px 15px; font-size: 13px; border: 1px solid #444;")
        self.input_box.returnPressed.connect(self.process_text)
        
        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(40, 40)
        self.btn_send.clicked.connect(self.process_text)
        self.btn_send.setStyleSheet("background:#0078D7; color:white; border-radius:20px; font-size:14px;")
        
        self.input_hbox.addWidget(self.input_box)
        self.input_hbox.addWidget(self.btn_send)
        self.chat_vbox.addLayout(self.input_hbox)
        
        self.pages.addWidget(self.page_chat)
        self.page_cmd = QWidget()
        self.cmd_layout = QVBoxLayout(self.page_cmd)
        self.browser = QTextBrowser()
        self.browser.setStyleSheet("background:transparent; border:none;") 
        
        html_content = """
        <style>
            h2 { color: #00FFFF; font-family: 'Segoe UI Black'; font-size: 14px; margin-bottom: 5px; }
            table { width: 100%; border-collapse: collapse; font-family: 'Segoe UI'; font-size: 10px; }
            td { padding: 6px 0px; vertical-align: top; }
            .cat { color: #ffffff; font-weight: bold; width: 70px; }
            .desc { color: #cccccc; }
            .footer { color: #666666; font-size: 10px; margin-top: 20px; }
            hr { border: 1px solid #333; }
        </style>
        <h2>COMMANDS CENTER</h2><hr>
        <table>
            <tr><td class='cat'>❔ AI</td><td class='desc'>: Ask anything...</td></tr>
            <tr><td class='cat'>🚀 APPS</td><td class='desc'>: Open Chrome, Close Notepad</td></tr>
            <tr><td class='cat'>🛠 TOOLS</td><td class='desc'>: Screenshot, Type [Text]</td></tr>
        </table>
        """
        self.browser.setHtml(html_content)
        self.cmd_layout.addWidget(self.browser)
        self.pages.addWidget(self.page_cmd)
        
        self.content_layout.addWidget(self.pages)
        
        self.sizegrip = QSizeGrip(self.content)
        bottom_right_layout = QHBoxLayout()
        bottom_right_layout.addStretch()
        bottom_right_layout.addWidget(self.sizegrip)
        bottom_right_layout.setContentsMargins(0,0,0,0)
        self.content_layout.addLayout(bottom_right_layout)

        self.hbox.addWidget(self.content)
        self.old_pos = None

    def init_logic(self):
        self.worker = SeeyaThread()
        self.worker.chat_signal.connect(self.add_message)
        self.worker.status_signal.connect(self.update_status)
        self.worker.glow_signal.connect(self.update_glow)
        self.worker.start()
        
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.cpu_bar.setValue(int(psutil.cpu_percent())))
        self.timer.start(2000)

    def toggle_maximize(self):
        if self.is_maximized_custom:
            self.setGeometry(self.old_geometry)
            self.is_maximized_custom = False
            self.layout_main.setContentsMargins(10, 10, 10, 10) 
            self.main_frame.setStyleSheet("QWidget#MainFrame { background-color: #0F0F0F; border-radius: 12px; border: 1px solid #333; }")
            self.btn_max.setText("☐")
            self.sizegrip.setVisible(True)
        else:
            self.old_geometry = self.geometry()
            screen = QApplication.primaryScreen().availableGeometry()
            self.setGeometry(screen)
            self.is_maximized_custom = True
            self.layout_main.setContentsMargins(0, 0, 0, 0)
            self.main_frame.setStyleSheet("QWidget#MainFrame { background-color: #0F0F0F; border: none; border-radius: 0px; }")
            self.btn_max.setText("❐")
            self.sizegrip.setVisible(False)

    def process_text(self):
        text = self.input_box.text().strip()
        if not text: return
        self.input_box.clear()
        self.add_message("You", text)
        threading.Thread(target=self.worker.process_command, args=(text,)).start()

    def add_message(self, sender, text):
        if sender == "Seeya":
            if self.current_thinking_widget:
                try:
                    self.msg_layout.removeWidget(self.current_thinking_widget)
                    self.current_thinking_widget.deleteLater()
                    self.current_thinking_widget = None
                except: pass

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0,0,0,0)

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setFont(QFont("Segoe UI", 10)) 
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)

        if sender == "You":
            bubble.setStyleSheet("background-color: #0078D7; color: white; padding: 10px 15px; border-radius: 15px; border-bottom-right-radius: 2px;")
            row_layout.addStretch()
            row_layout.addWidget(bubble)
        elif sender == "Thinking":
            bubble.setStyleSheet("background-color: #222; color: #888; padding: 8px 12px; border-radius: 15px; font-style: italic; border: 1px solid #444;")
            row_layout.addWidget(bubble)
            row_layout.addStretch()
            self.current_thinking_widget = row_widget
        else: 
            bubble.setStyleSheet("background-color: #333; color: #eee; padding: 10px 15px; border-radius: 15px; border-bottom-left-radius: 2px;")
            row_layout.addWidget(bubble)
            row_layout.addStretch()
        
        self.msg_layout.addWidget(row_widget)
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def update_glow(self, is_speaking):
        if is_speaking:
            self.shadow.setColor(QColor(0, 180, 180, 150))
            self.shadow.setBlurRadius(20)
        else:
            self.shadow.setColor(QColor(0, 0, 0, 150))
            self.shadow.setBlurRadius(20)

    def update_status(self, text):
        if not self.worker.is_mic_muted: self.lbl_status.setText(f"● {text.upper()}")

    def toggle_voice_output(self):
        is_silent = logic.toggle_voice_mute()
        if is_silent:
            self.btn_voice.setText("🔇 SILENT")
            self.btn_voice.setStyleSheet("background:#444; color:#888; border-radius:8px; font-weight:bold; font-size: 12px;")
        else:
            self.btn_voice.setText(" VOICE ON")
            self.btn_voice.setStyleSheet("background:#7E57C2; color:white; border-radius:8px; font-weight:bold; font-size: 12px;")

    def toggle_mic_input(self):
        self.worker.is_mic_muted = not self.worker.is_mic_muted
        if self.worker.is_mic_muted:
            self.btn_mic.setText("MIC MUTED")
            self.btn_mic.setStyleSheet("background:#FF5252; color:white; border-radius:8px; font-weight:bold; font-size:12px;")
            self.lbl_status.setText("● MIC OFF")
            self.lbl_status.setStyleSheet("color:#FF5252; font-weight:bold; font-size:11px;")
            self.input_box.setPlaceholderText("Mic Muted. Unmute or Type Command...")
        else:
            self.btn_mic.setText("LISTENING...")
            self.btn_mic.setStyleSheet("background:#222; color:#00E676; border:1px solid #00E676; border-radius:8px; font-weight:bold; font-size:12px;")
            self.lbl_status.setText("● ONLINE")
            self.lbl_status.setStyleSheet("color:#00E676; font-weight:bold; font-size:11px;")
            self.input_box.setPlaceholderText("Speak or Type Command...")

    def refresh_chat(self):
        while self.msg_layout.count():
            item = self.msg_layout.takeAt(0)
            if item.widget(): 
                item.widget().deleteLater()
        
        self.add_message("Seeya", "Chat Refreshed.")
        
        QTimer.singleShot(1000, lambda: self._remove_last_message())

    def _remove_last_message(self):
        count = self.msg_layout.count()
        if count > 0:
            item = self.msg_layout.takeAt(count - 1) # Last item uthao
            if item.widget():
                item.widget().deleteLater()

    def create_nav_btn(self, text, idx):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.pages.setCurrentIndex(idx))
        btn.setStyleSheet("""
            QPushButton{text-align:left; padding:10px; background:transparent; color:#888; font-weight:bold; font-size:13px;} 
            QPushButton:hover{color:white; background-color:#222; border-left: 2px solid cyan;}
        """)
        self.sidebar_layout.addWidget(btn)
        return btn

    def mousePressEvent(self, e):
        if self.is_maximized_custom: return
        if e.x() > self.width() - 20 and e.y() > self.height() - 20: return 
        self.old_pos = e.globalPos()

    def mouseMoveEvent(self, e):
        if self.old_pos:
            delta = e.globalPos() - self.old_pos
            self.move(self.x()+delta.x(), self.y()+delta.y())
            self.old_pos = e.globalPos()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SeeyaDashboard()
    window.show()
    sys.exit(app.exec_())