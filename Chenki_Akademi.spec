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
    'core.timetable_data',
    'state_manager'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    icon=['app_icon.ico'],
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
    icon='app_icon.ico',
    bundle_identifier=None,
)
