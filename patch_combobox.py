import os

file_path = "/Users/fookay/ders program/dialogs/edit_forms.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Window Flags
old_flags = """        self.popup = QListWidget()
        self.popup.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.popup.setFocusPolicy(Qt.NoFocus)
        self.popup.setAttribute(Qt.WA_ShowWithoutActivating, True)"""

new_flags = """        self.popup = QListWidget()
        self.popup.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.popup.setFocusPolicy(Qt.NoFocus)
        self.popup.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
        self.popup.setAttribute(Qt.WA_ShowWithoutActivating, True)"""

content = content.replace(old_flags, new_flags)

# Fix 2: eventFilter logic
old_event = """    def eventFilter(self, obj, event):
        from PySide6.QtCore import QTimer
        if obj == self.edit and event.type() == QEvent.FocusOut:
            QTimer.singleShot(150, self.popup.hide)
            
        if obj == self.edit and event.type() == QEvent.KeyPress:"""

new_event = """    def eventFilter(self, obj, event):
        from PySide6.QtCore import QTimer
        if obj == self.edit and event.type() == QEvent.FocusOut:
            def check_and_hide():
                # Don't hide if mouse is over the popup (so clicking/scrolling works)
                if not self.popup.underMouse():
                    self.popup.hide()
            QTimer.singleShot(200, check_and_hide)
            
        if obj == self.edit and event.type() == QEvent.KeyPress:"""

content = content.replace(old_event, new_event)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("ComboBox patch applied.")
