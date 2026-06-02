from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCore import Qt

class BellButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notification_count = 0
        self.setStyleSheet("background: transparent; border: none;")


    def set_notifications(self, count):
        self.notification_count = count
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.notification_count > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("red"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(self.width()-15, 0, 15, 15)
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", 7, QFont.Bold))
            painter.drawText(self.width()-15, 0, 15, 15, Qt.AlignCenter, str(self.notification_count))
            painter.end()