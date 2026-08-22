"""
test_grid_drag_feedback.py — gride sürüklerken yasak işareti çıkmamalı, preview görünmeli.

    python test_grid_drag_feedback.py

İki hata:
  1. _drop_anchor, tutma noktasını çıkarınca konum viewport DIŞINA düşüyordu
     (kartın alt yarısından tutmak yeterli). rowAt/columnAt -1 dönüyor, dragMoveEvent
     event.ignore() diyor, Qt yasak imleci gösteriyordu.
  2. set_drag_preview dolu hücrede preview'i kasten iptal ediyordu — oysa artık oraya
     bırakmak iki dersi TAKAS ediyor, yani geri bildirim asıl orada gerekli.
"""
import json
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QDragMoveEvent, QDropEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QTableWidgetItem  # noqa: E402

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    if cond:
        PASSED.append(name)
        print(f"  PASS  {name}")
    else:
        FAILED.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def run():
    app = QApplication.instance() or QApplication(sys.argv)
    from timetable_grid import DropTableWidget

    table = DropTableWidget(5, 40)
    table.resize(1400, 400)
    table.show()

    table.setItem(0, 0, QTableWidgetItem("Matematik"))   # kaynak
    table.setItem(0, 3, QTableWidgetItem("Fizik"))       # dolu hedef

    cell_w = table.columnWidth(3)
    cell_h = table.rowHeight(0)

    def drag_over(target_col, grab_dx, grab_dy, duration=1):
        info = {
            "subject_name": "Matematik", "teacher_name": "Ahmet Yılmaz",
            "class_name": "9A", "duration": duration, "is_move": True,
            "origin_row": 0, "origin_col": 0,
            "grab_dx": grab_dx, "grab_dy": grab_dy,
        }
        mime = QMimeData()
        mime.setData("application/x-lesson", json.dumps(info).encode())
        pos = table.visualRect(table.model().index(0, target_col)).center()

        table._drag_preview_info = None
        event = QDragMoveEvent(pos, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
        table.dragMoveEvent(event)
        return event, table._drag_preview_info, pos, mime

    print("\n[tutma noktası nerede olursa olsun drop kabul edilir]")
    # Kartın alt/sağ köşesinden tutmak, anchor'ı grid dışına taşıyordu.
    for label, (dx, dy) in [
        ("sol üst", (0, 0)),
        ("orta", (cell_w // 2, cell_h // 2)),
        ("sağ alt köşe", (cell_w - 2, cell_h - 2)),
        ("tam sağ alt", (cell_w, cell_h)),
    ]:
        event, preview, _, _ = drag_over(3, dx, dy)
        check(f"'{label}' tutuşta yasak işareti yok", event.isAccepted(),
              "dragMoveEvent reddetti")
        check(f"'{label}' tutuşta preview görünüyor", preview is not None)

    print("\n[dolu hücrede preview VAR ve takas olarak işaretli]")
    event, preview, _, _ = drag_over(3, cell_w // 2, cell_h // 2)
    check("dolu hedefte preview çiziliyor", preview is not None)
    check("preview takas olarak işaretli", bool(preview and preview.get("is_swap")),
          str(preview))

    print("\n[boş hücrede preview VAR ama takas değil]")
    event, preview, _, _ = drag_over(10, cell_w // 2, cell_h // 2)
    check("boş hedefte preview çiziliyor", preview is not None)
    check("boş hedef takas olarak işaretlenmiyor",
          bool(preview) and not preview.get("is_swap"), str(preview))

    print("\n[2 saatlik blok]")
    event, preview, _, _ = drag_over(3, cell_w, cell_h // 2, duration=2)
    check("2 saatlik blokta da kabul ediliyor", event.isAccepted())
    check("2 saatlik blokta preview var", preview is not None)

    print("\n[bırakma gerçekten sinyal üretiyor]")
    for label, (dx, dy) in [("orta", (cell_w // 2, cell_h // 2)),
                            ("sağ alt köşe", (cell_w - 2, cell_h - 2))]:
        info = {
            "subject_name": "Matematik", "teacher_name": "Ahmet Yılmaz",
            "class_name": "9A", "duration": 1, "is_move": True,
            "origin_row": 0, "origin_col": 0, "grab_dx": dx, "grab_dy": dy,
        }
        mime = QMimeData()
        mime.setData("application/x-lesson", json.dumps(info).encode())
        pos = table.visualRect(table.model().index(0, 3)).center()

        got = []
        table.lesson_dropped.connect(lambda r, c, i: got.append((r, c)))
        drop = QDropEvent(QPointF(pos), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
        table.dropEvent(drop)
        table.lesson_dropped.disconnect()

        check(f"'{label}' bırakışta drop kabul edildi", drop.isAccepted())
        check(f"'{label}' bırakışta geçerli hücre bulundu",
              bool(got) and got[0][0] >= 0 and got[0][1] >= 0, str(got))

    print("\n[anchor her zaman viewport içinde]")
    bounds = table.viewport().rect()
    worst = table._drop_anchor(QPoint(5, 5), {"grab_dx": 500, "grab_dy": 500})
    check("aşırı tutma offseti bile grid dışına taşmıyor",
          bounds.contains(worst), f"{worst.x()},{worst.y()} / {bounds}")

    table.close()


if __name__ == "__main__":
    try:
        run()
    except Exception:
        import traceback
        traceback.print_exc()
        FAILED.append(("beklenmeyen hata", "traceback"))
    finally:
        print("\n" + "=" * 60)
        print(f"geçen: {len(PASSED)}   kalan: {len(FAILED)}")
        for f in FAILED:
            print(f"  - {f}")
        print("=" * 60)
    sys.exit(1 if FAILED else 0)
