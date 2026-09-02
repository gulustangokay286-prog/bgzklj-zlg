"""
test_ui_smoke.py — constructs the real widgets offscreen and drives the drag-drop.

    python test_ui_smoke.py

Runs Qt with the "offscreen" platform plugin, so it needs no display and can be run
over SSH or in CI. It builds the actual HomeDashboard against a sandbox data
directory and simulates a version being dragged onto a folder, which is the path
that was silently broken.
"""
import json
import os
import shutil
import sys
import tempfile
import types

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SANDBOX = os.path.join(tempfile.gettempdir(), "chenki_ui_test")
shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)

import version_store  # noqa: E402

version_store._base_dir = lambda: os.path.join(SANDBOX, "institutions")


class _NullCloud:
    """Any attribute is a callable that succeeds and does nothing."""

    def __getattr__(self, _name):
        return lambda *a, **k: True


class _FakeApiClient:
    """Shaped like the real APIClient, but never touches the network."""

    base_url = "http://localhost.invalid"
    token = None

    def is_admin(self):
        return True

    def get_current_role(self):
        return "admin"

    def get_latest_release(self):
        return None

    def __getattr__(self, _name):
        return lambda *a, **k: True


# Keep every network path inert; this test is about widgets, not sync.
#
# cloud_sync and api_client MUST be stubbed, not just database: HomeDashboard starts
# a CloudSyncWorker and a RealtimeSyncClient, and version_store.create_institution
# pushes to the cloud from a background thread. Without these the test uploaded its
# fixtures to the REAL production VDS — "Smoke Okulu" showed up there and had to be
# removed by hand.
_fake_api_module = types.ModuleType("api_client")
_fake_api_module.api_client = _FakeApiClient()
_fake_api_module.token_manager = _fake_api_module.api_client
_fake_api_module.filename_to_key = lambda name: (name or "").replace(".", "_")

sys.modules["cloud_sync"] = _NullCloud()
sys.modules["api_client"] = _fake_api_module
sys.modules["database"] = _NullCloud()

from PySide6.QtCore import QMimeData, QPoint, Qt  # noqa: E402
from PySide6.QtGui import QDropEvent, QDragEnterEvent, QDragMoveEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

PASSED, FAILED = [], []


def _expand_all_groups(dash, app):
    """Version rows are built when a group is first opened, not when the
    list is refreshed — a collapsed group's rows genuinely do not exist.
    That is the point of the change (it took switching institutions from
    163ms to 28ms), so a test that wants rows has to open the groups the
    way a user would."""
    from home_dashboard import CollapsibleVersionGroup
    for g in dash.findChildren(CollapsibleVersionGroup):
        g._set_collapsed(False)
    app.processEvents()


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def make_drop_event(kind, widget, mime):
    pos = widget.rect().center()
    if kind == "enter":
        return QDragEnterEvent(pos, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
    if kind == "move":
        return QDragMoveEvent(pos, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
    return QDropEvent(pos, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)


def run():
    app = QApplication.instance() or QApplication(sys.argv)

    import home_dashboard
    from home_dashboard import (
        AppleVersionRow, CollapsibleVersionGroup, HomeDashboard, VERSION_DRAG_MIME,
    )

    print("\n[fixture]")
    inst = version_store.create_institution("Smoke Okulu")
    slug = inst["slug"]
    base = {
        "dersler": [{"ad": "Matematik"}], "siniflar": [{"ad": "9A"}],
        "ogretmenler": [{"ad": "Test Hoca"}], "atamalar": [],
        "settings": {"periods": 8}, "grid_placements": [],
    }
    for i in range(3):
        data = dict(base)
        data["grid_placements"] = [
            {"day": i, "period": 0, "subject_name": f"Ders{i}",
             "teacher_name": "Test Hoca", "class_name": "9A", "duration": 1}
        ]
        version_store.save_version(slug, data, note=f"v{i}", allow_duplicate=True)

    folder, _ = version_store.create_folder(slug, "Ağustos")
    check("fixture built", len(version_store.list_versions(slug)) >= 4)

    print("\n[dashboard construction]")
    dash = None
    try:
        dash = HomeDashboard(auth_data={"email": "test@local", "role": "admin", "is_offline": True})
        check("HomeDashboard constructs without error", True)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        check("HomeDashboard constructs without error", False, str(exc))
        return

    dash._selected_slug = slug
    dash._refresh_versions()
    app.processEvents()

    groups = dash.findChildren(CollapsibleVersionGroup)
    check("collapsed groups build no rows",
          len(dash.findChildren(AppleVersionRow)) == 0,
          f"{len(dash.findChildren(AppleVersionRow))} rows before expanding")
    _expand_all_groups(dash, app)
    rows = dash.findChildren(AppleVersionRow)
    check("version rows rendered once expanded", len(rows) > 0, f"{len(rows)} rows")
    check("folder group rendered", any(g.folder_id == folder["id"] for g in groups),
          str([g.folder_id for g in groups]))

    print("\n[drag and drop into a folder]")
    target = next((g for g in groups if g.folder_id == folder["id"]), None)
    source = next((r for r in rows if r.filename != version_store.get_active_version(slug)), None)
    check("a draggable non-active version exists", source is not None)
    if target is None or source is None:
        return

    mime = QMimeData()
    mime.setData(VERSION_DRAG_MIME, f"{slug}\n{source.filename}".encode("utf-8"))

    enter = make_drop_event("enter", target, mime)
    target.dragEnterEvent(enter)
    check("folder accepts the drag entering", enter.isAccepted())

    # This is the one that was missing. QWidget's default dragMoveEvent ignores the
    # event, and Qt only delivers a drop if the last drag-move was accepted — so
    # without an override the gesture died here, invisibly.
    move = make_drop_event("move", target, mime)
    target.dragMoveEvent(move)
    check("folder accepts drag-move (this is what enables the drop)", move.isAccepted())

    drop = make_drop_event("drop", target, mime)
    target.dropEvent(drop)
    app.processEvents()
    check("drop is accepted", drop.isAccepted())

    filed = {v["filename"]: v for v in version_store.list_versions(slug)}
    check("version is now filed in the folder",
          filed[source.filename]["folder_id"] == folder["id"],
          str(filed[source.filename].get("folder_id")))

    print("\n[drag rejects foreign payloads]")
    junk = QMimeData()
    junk.setText("some unrelated text")
    bad = make_drop_event("enter", target, junk)
    target.dragEnterEvent(bad)
    check("unrelated drag is refused", not bad.isAccepted())

    print("\n[drag source produces a visible ghost]")
    pixmap = source._make_drag_pixmap()
    check("drag pixmap is non-empty", not pixmap.isNull() and pixmap.width() > 0,
          f"{pixmap.width()}x{pixmap.height()}")

    print("\n[double-click opens]")
    opened = []
    source.double_clicked.connect(lambda s, f: opened.append((s, f)))
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QPointF, QEvent
    evt = QMouseEvent(
        QEvent.MouseButtonDblClick, QPointF(source.rect().center()),
        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier,
    )
    source.mouseDoubleClickEvent(evt)
    app.processEvents()
    check("double-click emits double_clicked", len(opened) == 1, str(opened))

    print("\n[selection does not restyle every row]")
    restyles = {"n": 0}
    original = AppleVersionRow._update_style

    def counting(self):
        restyles["n"] += 1
        return original(self)

    AppleVersionRow._update_style = counting
    try:
        # Flush pending deleteLater()s first. _refresh_versions rebuilds the list by
        # calling deleteLater() on the old rows, and Qt only destroys those when the
        # event loop next processes deferred deletions — until then findChildren()
        # still returns them. Counting restyles without flushing measures widgets
        # that are already on their way out, not the cost of a selection.
        from PySide6.QtCore import QEvent
        app.processEvents()
        app.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()

        _expand_all_groups(dash, app)
        rows = dash.findChildren(AppleVersionRow)
        # Start from a clean slate: earlier steps in this file selected a version, and
        # a row that is already selected has to be deselected here too — correct
        # behaviour, but it would make the count below reflect the previous test's
        # state rather than one selection.
        dash._selected_version = None
        for r in rows:
            r.set_selected(False)
        restyles["n"] = 0

        dash._on_version_selected(rows[0].filename)
        app.processEvents()
        first = restyles["n"]
        dash._on_version_selected(rows[0].filename)  # same row again
        check("re-selecting the same row restyles nothing", restyles["n"] == first,
              f"{first} then {restyles['n']}")
        check("selecting restyles at most two rows", first <= 2, f"{first} restyles")
    finally:
        AppleVersionRow._update_style = original

    print("\n[save overlay does not block]")
    import time
    from save_dialog import run_apple_save_sequence
    start = time.perf_counter()
    run_apple_save_sequence(dash, duration_seconds=1.0, title="Test", message="Test")
    elapsed = time.perf_counter() - start
    app.processEvents()
    # It used to busy-wait for the full duration on the GUI thread, with a 0.25s
    # floor even when the caller asked for less.
    check("returns immediately instead of blocking", elapsed < 0.15, f"{elapsed * 1000:.0f} ms")

    print("\n[folder state survives a refresh]")
    target = next((g for g in dash.findChildren(CollapsibleVersionGroup)
                   if g.folder_id == folder["id"]), None)
    if target is not None:
        target._set_collapsed(False)
        dash._refresh_versions()
        app.processEvents()
        after = next((g for g in dash.findChildren(CollapsibleVersionGroup)
                      if g.folder_id == folder["id"]), None)
        check("an open folder stays open across a rebuild",
              after is not None and not after.is_collapsed,
              "collapsed" if after is not None else "group missing")

    dash.close()


if __name__ == "__main__":
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        FAILED.append(("unhandled exception", "see traceback"))
    finally:
        print("\n" + "=" * 60)
        print(f"passed: {len(PASSED)}   failed: {len(FAILED)}")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        print("=" * 60)
        shutil.rmtree(SANDBOX, ignore_errors=True)
    sys.exit(1 if FAILED else 0)
