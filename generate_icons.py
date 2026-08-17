"""
generate_icons.py — macOS App Icon (.icns) Generator
Renders a 1024x1024 3D Master Icon and builds standard macOS .icns file using iconutil.
"""
import os
import sys
import subprocess
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter, QPixmap, QColor, QBrush, QPen, QPainterPath, QLinearGradient
from PySide6.QtCore import Qt, QRectF

def generate_master_icon(output_path: str = "app_icon.png", size: int = 1024):
    app = QApplication.instance() or QApplication(sys.argv)
    
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    
    # 1. Base Squircle Rounded Tile with Apple HIG Curvature and 3D Gradient
    grad_bg = QLinearGradient(0, 0, size, size)
    grad_bg.setColorAt(0.0, QColor("#1D4ED8"))  # Vibrant Blue
    grad_bg.setColorAt(0.5, QColor("#0071E3"))  # Apple Blue
    grad_bg.setColorAt(1.0, QColor("#0F172A"))  # Deep Navy
    
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(grad_bg))
    p.drawRoundedRect(QRectF(30, 30, size - 60, size - 60), 220, 220)
    
    # Outer Highlight Bevel (Glass Rim)
    p.setPen(QPen(QColor(255, 255, 255, 90), 16))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(40, 40, size - 80, size - 80), 210, 210)
    
    # 2. Isometric 3D Academy Building Symbol
    mid_x = size / 2.0
    
    # Roof Gable (Triangle)
    roof_path = QPainterPath()
    roof_path.moveTo(mid_x, 220)
    roof_path.lineTo(size - 210, 360)
    roof_path.lineTo(210, 360)
    roof_path.closeSubpath()
    
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 250))
    p.drawPath(roof_path)
    
    # Cornice / Beam
    p.setBrush(QColor(255, 255, 255, 220))
    p.drawRoundedRect(QRectF(190, 360, size - 380, 45), 10, 10)
    
    # 4 Classical Columns with 3D depth
    col_w = 68
    col_h = 240
    col_y = 430
    
    col_xs = [225, 395, 565, 735]
    for cx in col_xs:
        # Pillar
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(QRectF(cx, col_y, col_w, col_h), 12, 12)
        # Pillar highlight
        p.setPen(QPen(QColor(255, 255, 255, 120), 4))
        p.drawLine(cx + 10, col_y + 10, cx + 10, col_y + col_h - 10)
        p.setPen(Qt.NoPen)
        
    # Foundation Base Steps
    p.setBrush(QColor(255, 255, 255, 210))
    p.drawRoundedRect(QRectF(190, 690, size - 380, 40), 10, 10)
    p.setBrush(QColor(255, 255, 255, 250))
    p.drawRoundedRect(QRectF(160, 735, size - 320, 50), 14, 14)
    
    p.end()
    
    pix.save(output_path, "PNG")
    print(f"Master icon generated at: {output_path}")
    return output_path

def build_mac_icns(master_png: str = "app_icon.png", output_icns: str = "app_icon.icns"):
    iconset_dir = "app_icon.iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    
    from PIL import Image
    im = Image.open(master_png)
    
    sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    
    for s, name in sizes:
        resized = im.resize((s, s), Image.Resampling.LANCZOS)
        resized.save(os.path.join(iconset_dir, name), "PNG")
        
    # Run macOS native iconutil
    try:
        subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", output_icns], check=True)
        print(f"macOS .icns bundle successfully compiled: {output_icns}")
    except Exception as e:
        print(f"iconutil warning: {e}")

if __name__ == "__main__":
    generate_master_icon("app_icon.png")
    build_mac_icns("app_icon.png", "app_icon.icns")
