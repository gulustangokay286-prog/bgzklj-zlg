import sys
from PySide6.QtWidgets import QApplication, QComboBox, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import QCompleter

def normalize_tr(text):
    if not text: return ""
    text = str(text)
    tr_map = str.maketrans({'i': 'İ', 'ı': 'I', 'ç': 'Ç', 'ğ': 'Ğ', 'ö': 'Ö', 'ş': 'Ş', 'ü': 'Ü'})
    return text.translate(tr_map).upper()

class SearchableComboBox(QComboBox):
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setMaxVisibleItems(10)
        self._all_items = list(items or [])
        self.addItems(self._all_items)
        
        self._model = QStringListModel(self._all_items, self)
        self._completer = QCompleter(self._model, self)
        self._completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(self._completer)
        
        self.lineEdit().textEdited.connect(self._on_text_edited)
        
        # We need this to match the API
        self.currentTextChanged = self.lineEdit().textChanged
        
        self.setStyleSheet("""
            QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                padding: 2px 8px;
                background: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                color: #0F172A;
                min-height: 28px;
            }
            QComboBox::drop-down {
                border-left: 1px solid #CBD5E1;
                width: 28px;
                background: #F8FAFC;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }
            QComboBox::down-arrow {
                image: none;
            }
        """)

    def setItems(self, items):
        self._all_items = list(items)
        self.clear()
        self.addItems(self._all_items)
        self._model.setStringList(self._all_items)

    def addItems(self, items):
        super().addItems(items)
        if hasattr(self, '_all_items'):
            self._all_items = list(items)
            self._model.setStringList(self._all_items)

    def _filter_items(self, query):
        q_norm = normalize_tr(query.strip())
        if not q_norm:
            return list(self._all_items)
        prefix = [s for s in self._all_items if normalize_tr(s).startswith(q_norm)]
        substr = [s for s in self._all_items if q_norm in normalize_tr(s) and s not in prefix]
        return prefix + substr

    def _on_text_edited(self, text):
        matches = self._filter_items(text)
        self._model.setStringList(matches)
        self._completer.complete()

    def findText(self, text, flags=None):
        t_norm = normalize_tr(text.strip())
        for i, item in enumerate(self._all_items):
            if normalize_tr(item) == t_norm:
                return i
        return -1

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = QWidget()
    l = QVBoxLayout(w)
    cb = SearchableComboBox(["Matematik 1", "Matematik 2", "Fizik", "Kimya", "Biyoloji"])
    l.addWidget(cb)
    w.show()
    sys.exit(app.exec())
