import sys
from PySide6.QtWidgets import QApplication, QTableWidget, QMainWindow

app = QApplication(sys.argv)
w = QMainWindow()
t = QTableWidget(10, 10, w)
w.setCentralWidget(t)

def on_cell_clicked(r, c):
    print(f"cellClicked: {r}, {c}")

def on_current_cell_changed(r, c, pr, pc):
    print(f"currentCellChanged: {r}, {c} (prev {pr}, {pc})")

t.cellClicked.connect(on_cell_clicked)
t.currentCellChanged.connect(on_current_cell_changed)
w.show()

# Simulate a click on empty cell
print("Simulating click on 5, 5")
t.setCurrentCell(5, 5)
t.cellClicked.emit(5, 5)

