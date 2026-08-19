# -*- mode: python ; coding: utf-8 -*-


hidden_modules = [
    'dialogs.auto_schedule_dialog',
    'dialogs.master_data_dialog',
    'dialogs.edit_forms',
    'dialogs.print_preview',
    'dialogs.print_wizard',
    'dialogs.relations_dialog',
    'dialogs.constraints_dialog',
    'dialogs.color_picker_dialog',
    'dialogs.school_info',
    'dialogs.statistics_dialog',
    'dialogs.startup_wizard',
    'dialogs.faq_dialog',
    'dialogs.compare_dialog',
    'auto_scheduler',
    'timetable_grid',
    'ribbon_widget',
    'login_dialog',
    'database',
    'cloud_sync',
    'version_store',
    'home_dashboard',
    'core.timetable_data',
    'state_manager'
]

import sys
import os

icon_file = 'app_icon.icns' if sys.platform == 'darwin' and os.path.exists('app_icon.icns') else 'app_icon.ico'

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('dialogs', 'dialogs'),
        ('11.png', '.'),
        ('ChatGPT Image 16 Ağu 2026 10_31_17.png', '.'),
        ('app_icon.ico', '.'),
        ('app_icon.png', '.'),
        ('app_icon.icns', '.')
    ],
    hiddenimports=hidden_modules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Chenki_Akademi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Chenki_Akademi',
)
app = BUNDLE(
    coll,
    name='Chenki_Akademi.app',
    icon=icon_file,
    bundle_identifier='com.chenki.akademi',
)
