# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

try:
    ortools_datas, ortools_binaries, ortools_hiddenimports = collect_all('ortools')
except Exception:
    ortools_datas, ortools_binaries, ortools_hiddenimports = [], [], []

hidden_modules = [
    'perfect_scheduler',
    'kempe_scheduler',
    'tabu_repair',
    'chain_scheduler',
    'placement_engine',
    'dialogs.preflight_dialog',
    'dialogs.advanced_wizard',
    'dialogs.advisor_dialog',
    'dialogs.assignment_list_dialog',
    'dialogs.auto_schedule_dialog',
    'dialogs.base_dialog',
    'dialogs.bell_times_dialog',
    'dialogs.classes_dialog',
    'dialogs.color_picker_dialog',
    'dialogs.compare_dialog',
    'dialogs.constraints_dialog',
    'dialogs.customer_account_dialog',
    'dialogs.days_dialog',
    'dialogs.edit_forms',
    'dialogs.electives_dialog',
    'dialogs.export_dialog',
    'dialogs.extracted_dialog',
    'dialogs.faq_dialog',
    'dialogs.groups_dialog',
    'dialogs.master_data_dialog',
    'dialogs.notifications_dialog',
    'dialogs.print_preview',
    'dialogs.print_wizard',
    'dialogs.profile_dialog',
    'dialogs.relations_dialog',
    'dialogs.report_selection_dialog',
    'dialogs.room_assign_dialog',
    'dialogs.rooms_dialog',
    'dialogs.save_location_dialog',
    'dialogs.school_info',
    'dialogs.startup_wizard',
    'dialogs.statistics_dialog',
    'dialogs.subjects_dialog',
    'dialogs.teachers_dialog',
    'dialogs.test_timetable_dialog',
    'dialogs.timeoff_dialog',
    'dialogs.verify_timetable_dialog',
    'dialogs.wizard_dialog',
    'advisor',
    'api_client',
    'auto_scheduler',
    'cloud_sync',
    'constraint_sync',
    'database',
    'exporters',
    'home_dashboard',
    'lesson_hours',
    'login_dialog',
    'main_window',
    'bk_branding',
    'bk_update',
    'release_telemetry',
    'update_notifications',
    'ribbon_widget',
    'save_dialog',
    'splash_screen',
    'state_manager',
    'timetable_grid',
    'updater',
    'version',
    'version_store',
    'core.timetable_data',
] + ortools_hiddenimports

icon_file = 'app_icon.icns' if sys.platform == 'darwin' and os.path.exists('app_icon.icns') else 'app_icon.ico'

app_datas = [
    ('dialogs', 'dialogs'),
    ('11.png', '.'),
    ('ChatGPT Image 16 Ağu 2026 10_31_17.png', '.'),
    ('app_icon.ico', '.'),
    ('app_icon.png', '.'),
    ('app_icon.icns', '.'),
    ('bk_icon.png', '.'),
    ('bk_icon.ico', '.'),
    ('bk_inner_logo.png', '.'),
    ('bk_dashboard_brand.png', '.'),
] + ortools_datas

if os.path.exists('release_system_ca.pem'):
    app_datas.append(('release_system_ca.pem', '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=ortools_binaries,
    datas=app_datas,
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
