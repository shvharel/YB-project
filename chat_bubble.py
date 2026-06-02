from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class ChatBubble(QWidget):
    def __init__(self, message, is_mine, time_str, parent=None):
        super().__init__(parent)
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(10, 2, 10, 2)
        outer_layout.setSpacing(0)

        bubble_layout = QVBoxLayout()
        bubble_layout.setSpacing(2)

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setMaximumWidth(350)
        message_label.setMinimumWidth(60)

        time_label = QLabel(time_str)
        time_font = QFont()
        time_font.setPointSize(8)
        time_label.setFont(time_font)

        if is_mine:
            message_label.setStyleSheet("""
                background-color: #dcf8c6;
                color: black;
                border-radius: 10px;
                border-top-right-radius: 2px;
                padding: 6px 10px;
            """)
            time_label.setStyleSheet("color: #7a7a7a; padding-right: 4px;")
            time_label.setAlignment(Qt.AlignRight)
            bubble_layout.addWidget(message_label)
            bubble_layout.addWidget(time_label)
            outer_layout.addStretch()
            outer_layout.addLayout(bubble_layout)
        else:
            message_label.setStyleSheet("""
                background-color: #ffffff;
                color: black;
                border-radius: 10px;
                border-top-left-radius: 2px;
                padding: 6px 10px;
            """)
            time_label.setStyleSheet("color: #7a7a7a; padding-left: 4px;")
            time_label.setAlignment(Qt.AlignLeft)
            bubble_layout.addWidget(message_label)
            bubble_layout.addWidget(time_label)
            outer_layout.addLayout(bubble_layout)
            outer_layout.addStretch()


class DateSeparator(QWidget):
    def __init__(self, date_str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)

        label = QLabel(date_str)
        label.setStyleSheet("""
            background-color: #e1f0fa;
            color: #555;
            border-radius: 8px;
            padding: 3px 12px;
            font-size: 11px;
        """)
        label.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()