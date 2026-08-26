"""
dialogs/preflight_dialog.py — "bu ayarla ne olacak?" penceresi.

Kısıtlama / Zaman Tablosu ekranında Kaydet'e basmadan ve otomatik planlayıcıyı
başlatmadan önce çalışır. Yaptığınız ayar çizelgenin dolmasını imkânsız hale
getiriyorsa, kaç saatin nerede açıkta kalacağını sayıyla söyler ve devam düğmesini
5 saniye kilitler — okumadan geçilmesin diye. Süre dolunca devam edilebilir:
program hiçbir zaman kullanıcıyı durdurmaz, yalnızca ne olacağını söyler.

Sorun yoksa bu pencere HİÇ açılmaz; kayıt/plan doğrudan devam eder.
"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)

FONT_FAMILY = ".AppleSystemUIFont, SF Pro Text, -apple-system, Segoe UI, sans-serif"
COUNTDOWN_SECONDS = 5


def _fmt_report(report, days):
    """check_feasibility raporunu okunur satırlara çevirir."""
    lines = []
    cells = report.get("total_cells", 0)
    best = report.get("max_fillable", 0)
    demand = report.get("total_demand", 0)
    gap = max(0, min(cells, demand) - best)

    lines.append(("baslik", f"{gap} ders saati bu ayarlarla HİÇBİR ŞEKİLDE yerleşemez"))
    lines.append(("satir", f"{report.get('classes', 0)} sınıf × "
                           f"{report.get('open_hours_per_class', 0)} açık saat = {cells} hücre"))
    lines.append(("satir", f"Atanan ders: {demand} saat  •  "
                           f"En fazla dolabilecek: {best} saat"))

    over = report.get("overloaded_teachers") or []
    if over:
        lines.append(("ara", "Müsait olduğundan fazla ders atanmış öğretmenler"))
        for o in over[:8]:
            lines.append(("madde",
                          f"{o['teacher']}: {o['assigned']} saat atanmış, "
                          f"{o['available']} saat müsait → {o['shortfall']} saat sığmıyor"))
        if len(over) > 8:
            lines.append(("madde", f"... ve {len(over) - 8} öğretmen daha"))

    under = report.get("understaffed_slots") or []
    if under:
        lines.append(("ara", "O saatte derse girecek öğretmen yetmiyor"))
        for u in under[:6]:
            dname = days[u["day"]] if u["day"] < len(days) else f"{u['day'] + 1}. gün"
            lines.append(("madde",
                          f"{dname} {u['period'] + 1}. saat: {u['available']} müsait / "
                          f"{u['needed']} gerekli → {u['shortfall']} sınıf boş kalır"))
        if len(under) > 6:
            lines.append(("madde", f"... ve {len(under) - 6} saat daha"))

    idle = report.get("idle_teachers") or []
    if idle:
        lines.append(("ara", "Hiç dersi olmayan öğretmenler"))
        lines.append(("madde", ", ".join(idle[:8]) + (" ..." if len(idle) > 8 else "")))
        lines.append(("ipucu", "Yükün bir kısmını onlara aktarmak boşlukları kapatır."))
    return lines


class PreflightDialog(QDialog):
    """report: auto_scheduler.check_feasibility çıktısı.

    mode="save"  -> Kısıtlama/Zaman Tablosu kaydı öncesi
    mode="plan"  -> Otomatik planlayıcı başlamadan önce
    """

    def __init__(self, report, days, mode="save", parent=None, extra_note=""):
        super().__init__(parent)
        self.report = report or {}
        self._seconds = COUNTDOWN_SECONDS

        is_plan = (mode == "plan")
        self.setWindowTitle("Çizelge Kontrolü" if is_plan else "Bu Kısıtlama Çizelgeyi Bozuyor")
        self.setMinimumSize(620, 460)
        self.resize(680, 520)
        self.setStyleSheet(f"""
            QDialog {{ background: #F8FAFC; font-family: {FONT_FAMILY}; }}
            QLabel {{ color: #0F172A; }}
            QPushButton {{ border-radius: 8px; font-weight: 600; padding: 9px 18px;
                           font-family: {FONT_FAMILY}; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(12)

        head = QLabel("Planlayıcı bu ayarla çizelgeyi dolduramaz"
                      if not is_plan else "Bu ayarlarla çizelgenin tamamı dolmaz")
        head.setFont(QFont(FONT_FAMILY, 15, QFont.Bold))
        head.setStyleSheet("color: #B91C1C;")
        root.addWidget(head)

        sub = QLabel("Aşağıdakiler bir tercih meselesi değil, aritmetik: bir öğretmen "
                     "aynı anda tek sınıfta olabilir.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #475569; font-size: 12px;")
        root.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        blay = QVBoxLayout(body)
        blay.setContentsMargins(0, 0, 8, 0)
        blay.setSpacing(6)

        for kind, text in _fmt_report(self.report, days or []):
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            if kind == "baslik":
                lbl.setFont(QFont(FONT_FAMILY, 13, QFont.Bold))
                lbl.setStyleSheet("color: #B91C1C; background: #FEF2F2; border: 1px solid "
                                  "#FECACA; border-radius: 8px; padding: 10px 12px;")
            elif kind == "ara":
                lbl.setFont(QFont(FONT_FAMILY, 12, QFont.Bold))
                lbl.setStyleSheet("color: #0F172A; margin-top: 6px;")
            elif kind == "madde":
                lbl.setStyleSheet("color: #334155; font-size: 12px; padding-left: 10px;")
                lbl.setText("•  " + text)
            elif kind == "ipucu":
                lbl.setStyleSheet("color: #0369A1; font-size: 12px; padding-left: 10px;")
            else:
                lbl.setStyleSheet("color: #334155; font-size: 12px;")
            blay.addWidget(lbl)

        if extra_note:
            note = QLabel(extra_note)
            note.setWordWrap(True)
            note.setStyleSheet("color: #92400E; background: #FFFBEB; border: 1px solid "
                               "#FDE68A; border-radius: 8px; padding: 10px 12px; font-size: 12px;")
            blay.addWidget(note)

        blay.addStretch(1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        foot = QLabel("Devam ederseniz yerleşemeyen dersler alttaki "
                      "'Yerleştirilmeyenler' listesine düşer; hiçbiri silinmez.")
        foot.setWordWrap(True)
        foot.setStyleSheet("color: #64748B; font-size: 12px;")
        root.addWidget(foot)

        row = QHBoxLayout()
        row.setSpacing(10)
        self.btn_fix = QPushButton("Geri Dön ve Düzelt" if not is_plan else "Vazgeç")
        self.btn_fix.setStyleSheet(
            "background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1;")
        self.btn_fix.clicked.connect(self.reject)

        self._go_text = "Yine de Kaydet" if not is_plan else "Yoksay ve Devam Et"
        self.btn_go = QPushButton(f"{self._go_text} ({self._seconds})")
        self.btn_go.setEnabled(False)
        self.btn_go.setStyleSheet(
            "background: #E2E8F0; color: #94A3B8; border: 1px solid #CBD5E1;")
        self.btn_go.clicked.connect(self.accept)

        row.addWidget(self.btn_fix)
        row.addStretch(1)
        row.addWidget(self.btn_go)
        root.addLayout(row)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._seconds -= 1
        if self._seconds > 0:
            self.btn_go.setText(f"{self._go_text} ({self._seconds})")
            return
        self._timer.stop()
        self.btn_go.setText(self._go_text)
        self.btn_go.setEnabled(True)
        self.btn_go.setStyleSheet(
            "background: #B91C1C; color: #FFFFFF; border: 1px solid #991B1B;")

    # Sayaç dolmadan Enter'a basıp geçmek de sayılmasın.
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not self.btn_go.isEnabled():
            return
        super().keyPressEvent(event)


def run_preflight(data_store, institution_slug=None, parent=None, mode="save",
                  extra_note=""):
    """Sorun varsa pencereyi gösterir. Devam edilecekse True döner.

    Sorun yoksa hiçbir şey göstermeden True döner — kullanıcı bir şey bozmadıysa
    yoluna devam eder.
    """
    try:
        from auto_scheduler import check_feasibility
        report = check_feasibility(data_store, institution_slug)
    except Exception as exc:
        # Kontrolün kendisi patlarsa kullanıcıyı ASLA engelleme.
        print(f"[preflight] kontrol çalışmadı: {exc}")
        return True

    if report.get("ok"):
        return True

    try:
        import constraint_sync
        days = constraint_sync.day_names(data_store)
    except Exception:
        days = []

    dlg = PreflightDialog(report, days, mode=mode, parent=parent, extra_note=extra_note)
    return dlg.exec() == QDialog.Accepted
