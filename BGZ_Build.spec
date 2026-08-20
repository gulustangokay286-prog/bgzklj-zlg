# -*- mode: python ; coding: utf-8 -*-
# BGZ Ders Planlama - Windows Build Spec
# Includes 11.png (login/splash logo) and all dialogs

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('dialogs', 'dialogs'),
        ('11.png', '.'),
        ('app_icon.png', '.'),
        ('app_icon.ico', '.'),
    ],
    hiddenimports=[
        'auto_scheduler',
        'version_store',
        'cloud_sync',
        'api_client',
        'home_dashboard',
        'login_dialog',
        'splash_screen',
        'save_dialog',
        'timetable_grid',
        'main_window',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='BGZ_Ders_Planlama',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)
