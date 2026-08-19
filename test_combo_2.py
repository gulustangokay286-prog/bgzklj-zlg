import sys
from PySide6.QtWidgets import QApplication
from dialogs.edit_forms import SearchableComboBox

app = QApplication(sys.argv)
cb = SearchableComboBox(["Test 1", "Test 2"])
print("ComboBox initialized successfully.")
