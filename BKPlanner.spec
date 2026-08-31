# -*- mode: python ; coding: utf-8 -*-
# BK Planner — main application build.
#
# Key differences from the old Chenki_Akademi.spec:
#   - exe is named BKPlanner.exe (Task Manager / shortcut identity)
#   - carries a real Windows version resource (version_info_app.txt), so
#     Explorer > Properties > Details is populated and Task Manager shows
#     "BK Planner", not a bare filename
#   - icon is bk_icon.ico (the supplied brand mark, black corners removed)
#   - the ReleaseSystem `client` update package is compiled straight into
#     this exe (pathex + collected submodules), so bk_update.py runs the
#     update engine IN-PROCESS with no separate Updater.exe agent
import os
import sys

HERE = os.path.abspath(SPECPATH)
RELEASE_SYSTEM = os.path.abspath(os.path.join(HERE, "..", "ReleaseSystem"))

hidden_modules = [
    'ortools', 'ortools.sat', 'ortools.sat.python', 'ortools.sat.python.cp_model',
    'ortools.init', 'ortools.init.python',
    'perfect_scheduler', 'kempe_scheduler', 'tabu_repair', 'chain_scheduler', 'placement_engine',
    'dialogs.preflight_dialog', 'dialogs.advanced_wizard', 'dialogs.advisor_dialog',
    'dialogs.assignment_list_dialog', 'dialogs.auto_schedule_dialog', 'dialogs.base_dialog',
    'dialogs.bell_times_dialog', 'dialogs.classes_dialog', 'dialogs.color_picker_dialog',
    'dialogs.compare_dialog', 'dialogs.constraints_dialog', 'dialogs.days_dialog',
    'dialogs.edit_forms', 'dialogs.electives_dialog', 'dialogs.export_dialog',
    'dialogs.extracted_dialog', 'dialogs.faq_dialog', 'dialogs.groups_dialog',
    'dialogs.master_data_dialog', 'dialogs.notifications_dialog', 'dialogs.print_preview',
    'dialogs.print_wizard', 'dialogs.profile_dialog', 'dialogs.relations_dialog',
    'dialogs.report_selection_dialog', 'dialogs.room_assign_dialog', 'dialogs.rooms_dialog',
    'dialogs.save_location_dialog', 'dialogs.school_info', 'dialogs.startup_wizard',
    'dialogs.statistics_dialog', 'dialogs.subjects_dialog', 'dialogs.teachers_dialog',
    'dialogs.test_timetable_dialog', 'dialogs.timeoff_dialog', 'dialogs.verify_timetable_dialog',
    'dialogs.wizard_dialog',
    'advisor', 'api_client', 'auto_scheduler', 'cloud_sync', 'constraint_sync', 'database',
    'exporters', 'home_dashboard', 'lesson_hours', 'login_dialog', 'main_window',
    'bk_branding', 'bk_update', 'update_notifications', 'ribbon_widget', 'save_dialog',
    'splash_screen', 'state_manager', 'timetable_grid', 'version', 'version_store',
    'core.timetable_data',
]
# The in-process update engine — ONLY the client submodules it actually
# imports. Deliberately NOT collect_submodules('client'): that would pull
# in client.networking.ws_client (the old standalone-agent's WebSocket
# connection, now unused) which imports the `websocket` package that isn't
# — and needn't be — installed for the app build.
hidden_modules += [
    'client', 'client.config',
    'client.networking', 'client.networking.http_client',
    'client.security', 'client.security.signature', 'client.security.device_identity',
    'client.state', 'client.state.paths', 'client.state.atomic_json',
    'client.updater', 'client.updater.engine', 'client.updater.downloader',
    'client.updater.installer', 'client.updater.manifest', 'client.updater.chunk_store',
    'client.updater.rollback', 'client.updater.state_machine', 'client.updater.verifier',
]

icon_file = 'bk_icon.ico'

app_datas = [
    ('dialogs', 'dialogs'),
    ('bk_icon.ico', '.'),
    ('bk_icon.png', '.'),
    ('bk_inner_logo.png', '.'),
    ('bk_shield_clean.png', '.'),
    ('ChatGPT Image 9 Tem 2026 19_56_13-3.png', '.'),
    ('bk_lockup.png', '.'),
    ('bk_dashboard_brand.png', '.'),
    # Ed25519 public key the in-process update engine verifies manifests
    # against — must land at client/keys/ so signature.py's module-relative
    # path (Path(__file__).parent.parent / "keys" / ...) resolves inside
    # the frozen bundle exactly as it does from source.
    (os.path.join(RELEASE_SYSTEM, 'client', 'keys', 'release_public_key.pem'), os.path.join('client', 'keys')),
]

a = Analysis(
    ['main.py'],
    pathex=[RELEASE_SYSTEM],  # makes `import client...` resolve into the update package
    binaries=[],
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
    name='BKPlanner',
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
    version='version_info_app.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='BKPlanner',
)
