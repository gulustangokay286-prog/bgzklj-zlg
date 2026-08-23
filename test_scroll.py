from PySide6.QtWidgets import *
import sys

app = QApplication(sys.argv)
dlg = QDialog()
dlg.resize(400, 300)
main_layout = QVBoxLayout(dlg)

scroll = QScrollArea()
scroll.setWidgetResizable(True)

scroll_content = QWidget()
content_lay = QVBoxLayout(scroll_content)
content_lay.setContentsMargins(0, 0, 0, 0)
content_lay.setSpacing(14)

for i in range(4):
    frame = QFrame()
    frame.setStyleSheet(".QFrame { background: #FFFFFF; border: 1px solid red; }")
    lay = QFormLayout(frame)
    for j in range(5):
        lay.addRow(QLabel(f"Label {j}"), QLineEdit())
    content_lay.addWidget(frame)

content_lay.addStretch(1)

scroll.setWidget(scroll_content)
main_layout.addWidget(scroll, 1)

bottom = QHBoxLayout()
btn = QPushButton("Tamam")
bottom.addWidget(btn)
# NO TOP STRETCH in main_layout
main_layout.addLayout(bottom)

dlg.show()

# Print height info after show
print(f'Scroll viewport height: {scroll.viewport().height()}')
print(f'Content widget height: {scroll_content.height()}')
for i in range(content_lay.count()):
    item = content_lay.itemAt(i)
    if item.widget():
        print(f'Widget {i} height: {item.widget().height()}')

sys.exit(0)
