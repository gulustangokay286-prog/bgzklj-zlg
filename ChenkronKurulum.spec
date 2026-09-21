# -*- mode: python ; coding: utf-8 -*-
"""
ChenkronKurulum.spec — özel kurulum yöneticisini tek dosyalık bir exe yapar.

Programın kendisi (dist\\Chenkron) buraya payload.zip olarak gömülür; o zip'i
build_installer.py üretir, bu spec doğrudan çalıştırılmaz. Sıra:

    python tools\\build_scheduler.py
    pyinstaller Chenkron.spec --noconfirm
    python build_installer.py

Zip olarak gömülmesinin sebebi custom_installer._payload_zip()'te yazılı:
PyInstaller tek-dosya modunda gömülü ne varsa çalışmadan önce temp'e açar,
ve 4000 ayrı dosya yerine tek bir arşiv açmak bu bekleme süresini bir
dakikadan birkaç saniyeye indiriyor.
"""
import os

HERE = os.path.abspath(SPECPATH)

payload = os.path.join(HERE, "build_payload", "payload.zip")
if not os.path.exists(payload):
    raise SystemExit(
        "payload.zip yok. Bu spec'i tek başına çalıştırmayın:\n"
        "    python build_installer.py\n"
        "(o betik önce dist\\Chenkron'u zipler, sonra buraya gelir)"
    )

datas = [(payload, ".")]

# Installer'ın kendi görselleri. Programın 384 MB'lık içeriği payload.zip'te;
# buraya yalnızca kurulum penceresinin çizdiği birkaç şey giriyor.
for name in ("chenkron_logo_white.png", "bk_icon.png", "icon.ico", "icon.png"):
    p = os.path.join(HERE, name)
    if os.path.exists(p):
        datas.append((p, "."))

icon_file = None
for cand in ("icon.ico", "bk_icon.ico"):
    p = os.path.join(HERE, cand)
    if os.path.exists(p):
        icon_file = p
        break

a = Analysis(
    ["custom_installer.py"],
    pathex=[HERE],
    binaries=[],
    datas=datas,
    # ui_icons doğrudan değil, try/except içinde import ediliyor; PyInstaller
    # onu kendiliğinden bulamıyor ve ikonsuz bir installer çıkıyor.
    hiddenimports=["ui_icons"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Installer'a uygulamanın ağırlığı girmesin: bunların hiçbiri
        # kurulum penceresinde kullanılmıyor.
        "ortools", "numpy", "pandas", "openpyxl", "matplotlib",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore", "PySide6.QtMultimedia", "PySide6.QtQuick",
        "PySide6.QtQml", "PySide6.QtCharts", "PySide6.QtDataVisualization",
        "PySide6.QtNetwork", "PySide6.QtSql", "PySide6.QtTest",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ChenkronKurulum",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
    # uac_admin YOK, bilerek: kurulum kullanıcının kendi klasörüne
    # (%LOCALAPPDATA%\Programs\Chenkron) yapılıyor. Yönetici hakkı
    # istememek yalnızca kurulumu kolaylaştırmıyor; programın kendi
    # klasörüne yazabilmesi otomatik güncellemenin de UAC sormadan
    # tamamlanması demek (bkz. ota_update.apply_staged).
)
