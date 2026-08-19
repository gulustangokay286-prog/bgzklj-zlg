import os

file_path = "/Users/fookay/ders program/dialogs/print_preview.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix minimum font size and allow word wrap
old_font = """                            font_sz = 10.0
                            painter.setFont(make_font(font_sz, True))
                            while painter.fontMetrics().horizontalAdvance(cell_text) > (block_w - 2) and font_sz > 7.0:
                                font_sz -= 0.5
                                painter.setFont(make_font(font_sz, True))
                            painter.setPen(QPen(QColor("#0F172A"), 1))
                            
                            painter.save()
                            painter.setClipRect(QRectF(px + 1, cur_y + 1, block_w - 2, row_h - 2))
                            painter.drawText(QRectF(px + 1, cur_y + 1, block_w - 2, row_h - 2), Qt.AlignCenter, cell_text)
                            painter.restore()"""

new_font = """                            font_sz = 10.0
                            painter.setFont(make_font(font_sz, True))
                            # Add newlines instead of + if it's too long
                            if "+" in cell_text and painter.fontMetrics().horizontalAdvance(cell_text) > (block_w - 2):
                                cell_text = cell_text.replace("+", "\\n")
                            
                            while painter.fontMetrics().horizontalAdvance(cell_text) > (block_w - 2) and font_sz > 4.5:
                                font_sz -= 0.5
                                painter.setFont(make_font(font_sz, True))
                            painter.setPen(QPen(QColor("#0F172A"), 1))
                            
                            painter.save()
                            painter.setClipRect(QRectF(px + 1, cur_y + 1, block_w - 2, row_h - 2))
                            painter.drawText(QRectF(px + 1, cur_y + 1, block_w - 2, row_h - 2), Qt.AlignCenter | Qt.TextWordWrap, cell_text)
                            painter.restore()"""
content = content.replace(old_font, new_font)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied for master list font shrinking.")
