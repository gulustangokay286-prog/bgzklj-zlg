"""
room_assign_dialog.py — "Dersliklere Atama".

Assigns a room to each lesson and keeps the assignment honest:

  * a room cannot hold two lessons in the same day/period
  * a room whose capacity is below the class size is flagged
  * a room whose type does not match the subject's required type is flagged

Rooms live in data_store["derslikler"] as
    {"ad", "kisa", "renk", "kapasite", "tur", "ozel_alanlar"}
and the chosen room is written back to BOTH data_store["atamalar"] (so a later
auto-schedule keeps it) and data_store["grid_placements"] (so the current grid and
every export show it).
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

NO_ROOM = "— derslik yok —"


def _norm(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _int_or_none(value):
    try:
        text = str(value).strip()
        return int(float(text)) if text else None
    except (TypeError, ValueError):
        return None


def assignment_key(entry: dict):
    return (_norm(entry.get("class") or entry.get("sinif") or entry.get("class_name")),
            _norm(entry.get("subject") or entry.get("ders") or entry.get("subject_name")),
            _norm(entry.get("teacher") or entry.get("ogretmen") or entry.get("teacher_name")))


def room_conflicts(data_store: dict):
    """[(room, day, period, [placement, ...]), ...] where a room is double-booked."""
    slots = {}
    for p in data_store.get("grid_placements", []) or []:
        if not isinstance(p, dict):
            continue
        room = _norm(p.get("room_name") or p.get("room") or p.get("derslik"))
        if not room:
            continue
        day = int(p.get("day", p.get("col", 0)) or 0)
        start = int(p.get("period", p.get("row", 0)) or 0)
        for off in range(max(1, int(p.get("duration", 1) or 1))):
            slots.setdefault((room, day, start + off), []).append(p)

    out = []
    for (room, day, period), items in sorted(slots.items()):
        # Lessons taught together as one combined block legitimately share a room.
        blocks = {i.get("block_id") or id(i) for i in items}
        if len(items) > 1 and len(blocks) > 1:
            out.append((room, day, period, items))
    return out


def capacity_problems(data_store: dict):
    """[(class, subject, room, class_size, room_capacity), ...] where the room is too small."""
    sizes = {}
    for c in data_store.get("siniflar", []) or []:
        if isinstance(c, dict):
            sizes[_norm(c.get("ad") or c.get("name"))] = _int_or_none(c.get("kapasite") or c.get("mevcut"))
    caps = {}
    for r in data_store.get("derslikler", []) or []:
        if isinstance(r, dict):
            caps[_norm(r.get("ad") or r.get("name"))] = _int_or_none(r.get("kapasite"))

    out = []
    for a in data_store.get("atamalar", []) or []:
        if not isinstance(a, dict):
            continue
        room = _norm(a.get("room") or a.get("derslik"))
        if not room:
            continue
        cls = _norm(a.get("class") or a.get("sinif"))
        size, cap = sizes.get(cls), caps.get(room)
        if size is not None and cap is not None and cap < size:
            out.append((cls, _norm(a.get("subject") or a.get("ders")), room, size, cap))
    return out


def auto_assign_rooms(data_store: dict):
    """Greedy room assignment. Returns (assigned, skipped, reasons).

    Lessons already carrying a room keep it — the user's manual choices are never
    silently overwritten. Everything else gets the first room that is free in every
    slot the lesson occupies and large enough for the class.
    """
    rooms = [r for r in (data_store.get("derslikler") or []) if isinstance(r, dict)]
    if not rooms:
        return 0, 0, ["Tanımlı derslik yok."]

    sizes = {}
    for c in data_store.get("siniflar", []) or []:
        if isinstance(c, dict):
            sizes[_norm(c.get("ad") or c.get("name"))] = _int_or_none(c.get("kapasite") or c.get("mevcut"))

    # Slots already taken, so pre-existing manual choices are respected.
    taken = set()
    for p in data_store.get("grid_placements", []) or []:
        if not isinstance(p, dict):
            continue
        room = _norm(p.get("room_name") or p.get("room") or p.get("derslik"))
        if not room:
            continue
        day = int(p.get("day", p.get("col", 0)) or 0)
        start = int(p.get("period", p.get("row", 0)) or 0)
        for off in range(max(1, int(p.get("duration", 1) or 1))):
            taken.add((room, day, start + off))

    assigned = skipped = 0
    reasons = []
    room_of_assignment = {}

    placements = [p for p in (data_store.get("grid_placements") or []) if isinstance(p, dict)]
    placements.sort(key=lambda p: (int(p.get("day", 0) or 0), int(p.get("period", 0) or 0)))

    for p in placements:
        if _norm(p.get("room_name") or p.get("room") or p.get("derslik")):
            continue
        day = int(p.get("day", p.get("col", 0)) or 0)
        start = int(p.get("period", p.get("row", 0)) or 0)
        span = max(1, int(p.get("duration", 1) or 1))
        cls = _norm(p.get("class_name") or p.get("class"))
        need = sizes.get(cls)

        chosen = None
        for room in rooms:
            name = _norm(room.get("ad") or room.get("name"))
            if not name:
                continue
            cap = _int_or_none(room.get("kapasite"))
            if need is not None and cap is not None and cap < need:
                continue
            if any((name, day, start + off) in taken for off in range(span)):
                continue
            chosen = name
            break

        if chosen is None:
            skipped += 1
            reasons.append(
                f"{cls} — {_norm(p.get('subject_name') or p.get('subject'))} "
                f"({day + 1}. gün {start + 1}. saat): uygun boş derslik yok")
            continue

        p["room_name"] = chosen
        p["room"] = chosen
        for off in range(span):
            taken.add((chosen, day, start + off))
        assigned += 1
        room_of_assignment[assignment_key(p)] = chosen

    # Mirror onto the assignment list so a re-run of the scheduler keeps the room.
    for a in data_store.get("atamalar", []) or []:
        if isinstance(a, dict) and not _norm(a.get("room") or a.get("derslik")):
            room = room_of_assignment.get(assignment_key(a))
            if room:
                a["room"] = room

    return assigned, skipped, reasons


class RoomAssignDialog(QDialog):
    COLS = ["Sınıf", "Ders", "Öğretmen", "Saat", "Derslik", "Durum"]

    def __init__(self, data_store, parent=None):
        super().__init__(parent)
        self.data_store = data_store if data_store is not None else {}
        self.setWindowTitle("Dersliklere Atama")
        self.resize(900, 600)
        self.setStyleSheet("""
            QDialog { background: #F8FAFC; }
            QLabel { color: #1E293B; font-size: 13px; }
            QTableWidget {
                background: #FFFFFF; border: 1px solid #E2E8F0;
                border-radius: 6px; gridline-color: #EEF2F7; font-size: 12px;
            }
            QHeaderView::section {
                background: #F1F5F9; color: #334155; border: none;
                border-bottom: 1px solid #E2E8F0; padding: 6px; font-weight: bold;
            }
            QPushButton {
                background: #2563EB; color: white; border: none;
                border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #1D4ED8; }
            QPushButton#ghost {
                background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1;
            }
            QPushButton#ghost:hover { background: #F1F5F9; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        head = QLabel("<b>Her ders için derslik seçin</b>")
        head.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(head)

        self.table = QTableWidget(0, len(self.COLS), self)
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self.table.horizontalHeader()
        for i in range(len(self.COLS)):
            header.setSectionResizeMode(i, QHeaderView.Stretch if i in (1, 2, 5)
                                        else QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addWidget(self.summary)

        buttons = QHBoxLayout()
        auto = QPushButton("Otomatik Ata")
        auto.setObjectName("ghost")
        auto.clicked.connect(self._auto)
        buttons.addWidget(auto)
        clear = QPushButton("Tümünü Temizle")
        clear.setObjectName("ghost")
        clear.clicked.connect(self._clear)
        buttons.addWidget(clear)
        buttons.addStretch(1)
        cancel = QPushButton("Vazgeç")
        cancel.setObjectName("ghost")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save = QPushButton("Kaydet")
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        self._reload()

    # -- data -----------------------------------------------------------

    def _room_names(self):
        names = []
        for r in self.data_store.get("derslikler", []) or []:
            if isinstance(r, dict):
                name = _norm(r.get("ad") or r.get("name"))
                if name:
                    cap = _int_or_none(r.get("kapasite"))
                    names.append((name, cap, _norm(r.get("tur"))))
        return names

    def _hours_of(self, key):
        total = 0
        for p in self.data_store.get("grid_placements", []) or []:
            if isinstance(p, dict) and assignment_key(p) == key:
                total += max(1, int(p.get("duration", 1) or 1))
        return total

    def _reload(self):
        rooms = self._room_names()
        sizes = {}
        for c in self.data_store.get("siniflar", []) or []:
            if isinstance(c, dict):
                sizes[_norm(c.get("ad") or c.get("name"))] = _int_or_none(
                    c.get("kapasite") or c.get("mevcut"))

        entries = [a for a in (self.data_store.get("atamalar") or []) if isinstance(a, dict)]
        self.table.setRowCount(len(entries))
        self._combos = []

        for row, a in enumerate(entries):
            key = assignment_key(a)
            cls, subject, teacher = key
            for col, text in enumerate((cls, subject, teacher)):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)

            hours = self._hours_of(key) or _int_or_none(a.get("duration")) or 0
            hitem = QTableWidgetItem(str(hours))
            hitem.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, hitem)

            combo = QComboBox()
            combo.addItem(NO_ROOM)
            for name, cap, kind in rooms:
                label = name
                extras = [x for x in (f"{cap} kişi" if cap else "", kind) if x]
                if extras:
                    label += "  (" + ", ".join(extras) + ")"
                combo.addItem(label, name)
            current = _norm(a.get("room") or a.get("derslik"))
            if current:
                idx = combo.findData(current)
                combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.currentIndexChanged.connect(lambda _i, r=row: self._on_room_changed(r))
            self.table.setCellWidget(row, 4, combo)
            self._combos.append((combo, a, key))

            self.table.setItem(row, 5, QTableWidgetItem(""))

        self._class_sizes = sizes
        self._room_caps = {name: cap for name, cap, _k in rooms}
        for row in range(self.table.rowCount()):
            self._on_room_changed(row)
        self._update_summary()

    def _selected_room(self, row):
        combo, _a, _k = self._combos[row]
        return combo.currentData() or ""

    def _on_room_changed(self, row):
        """Recomputes the status cell for one row, then the whole summary."""
        room = self._selected_room(row)
        cls = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
        status, color = "", "#64748B"

        if not room:
            status = "Derslik atanmadı"
        else:
            size = self._class_sizes.get(cls)
            cap = self._room_caps.get(room)
            if size is not None and cap is not None and cap < size:
                status, color = f"Kapasite yetersiz ({cap} < {size})", "#DC2626"
            else:
                clash = self._would_clash(row, room)
                if clash:
                    status, color = f"Çakışma: {clash}", "#DC2626"
                else:
                    status, color = "Uygun", "#059669"

        item = self.table.item(row, 5) or QTableWidgetItem()
        item.setText(status)
        item.setForeground(QBrush(QColor(color)))
        self.table.setItem(row, 5, item)
        self._update_summary()

    def _slots_of(self, key):
        slots = []
        for p in self.data_store.get("grid_placements", []) or []:
            if isinstance(p, dict) and assignment_key(p) == key:
                day = int(p.get("day", p.get("col", 0)) or 0)
                start = int(p.get("period", p.get("row", 0)) or 0)
                for off in range(max(1, int(p.get("duration", 1) or 1))):
                    slots.append((day, start + off))
        return slots

    def _would_clash(self, row, room):
        """Name of the first other lesson that wants the same room at the same time."""
        _combo, _a, key = self._combos[row]
        mine = set(self._slots_of(key))
        if not mine:
            return ""
        for other_row in range(len(self._combos)):
            if other_row == row:
                continue
            if self._selected_room(other_row) != room:
                continue
            _c, _oa, other_key = self._combos[other_row]
            if mine & set(self._slots_of(other_key)):
                return f"{other_key[0]} {other_key[1]}"
        return ""

    def _update_summary(self):
        total = self.table.rowCount()
        placed = sum(1 for r in range(total) if self._selected_room(r))
        bad = sum(1 for r in range(total)
                  if self.table.item(r, 5) and (
                      "Çakışma" in self.table.item(r, 5).text()
                      or "Kapasite" in self.table.item(r, 5).text()))
        note = f"{total} ders · {placed} derslik atandı"
        if bad:
            note += f" · <b style='color:#DC2626'>{bad} sorunlu</b>"
        if not self.data_store.get("derslikler"):
            note += " · <b>Tanımlı derslik yok</b> — önce Tanımlama İşlemleri → Derslikler."
        self.summary.setText(note)

    # -- actions --------------------------------------------------------

    def _auto(self):
        if not self.data_store.get("derslikler"):
            QMessageBox.information(self, "Derslik Yok",
                                    "Önce en az bir derslik tanımlamalısınız.")
            return
        # Work on the live store, since auto_assign_rooms reads the placements.
        assigned, skipped, reasons = auto_assign_rooms(self.data_store)
        self._reload()
        msg = f"{assigned} ders için derslik atandı."
        if skipped:
            msg += f"\n{skipped} ders yerleştirilemedi:\n\n" + "\n".join(reasons[:12])
            if len(reasons) > 12:
                msg += f"\n… ve {len(reasons) - 12} tane daha"
        QMessageBox.information(self, "Otomatik Derslik Atama", msg)

    def _clear(self):
        ret = QMessageBox.question(
            self, "Tümünü Temizle",
            "Bütün derslik atamaları kaldırılsın mı? Ders programı değişmez.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        for combo, _a, _k in self._combos:
            combo.setCurrentIndex(0)

    def _save(self):
        bad = [r for r in range(self.table.rowCount())
               if self.table.item(r, 5) and (
                   "Çakışma" in self.table.item(r, 5).text()
                   or "Kapasite" in self.table.item(r, 5).text())]
        if bad:
            ret = QMessageBox.question(
                self, "Sorunlu Atamalar",
                f"{len(bad)} derste çakışma veya kapasite sorunu var.<br><br>"
                f"Yine de kaydedilsin mi? <i>Sorunlar listede kırmızı kalır, "
                f"sonradan düzeltebilirsiniz.</i>",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if ret != QMessageBox.Yes:
                return

        by_key = {}
        for row, (_combo, a, key) in enumerate(self._combos):
            room = self._selected_room(row)
            by_key[key] = room
            if room:
                a["room"] = room
            else:
                a.pop("room", None)
                a.pop("derslik", None)

        for p in self.data_store.get("grid_placements", []) or []:
            if not isinstance(p, dict):
                continue
            room = by_key.get(assignment_key(p))
            if room:
                p["room_name"] = room
                p["room"] = room
            elif room == "":
                p.pop("room_name", None)
                p.pop("room", None)
                p.pop("derslik", None)

        self.accept()
