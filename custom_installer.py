# -*- coding: utf-8 -*-
"""
custom_installer.py — Chenkron Özel Kurulum Yöneticisi

Tamamen özgün tasarım: Login ekranından bağımsız, kurulum sürecine özel
modern minimalist UI. Sol panel koyu slate gradyan, sağ panel temiz beyaz
form alanı. Emoji yok, tüm ikonlar vektör.
"""

import os
import sys
import time
import math
import shutil
import subprocess

from PySide6.QtCore import (
    Qt, QRectF, QPointF, QSize, QTimer, QThread, Signal,
)
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QCursor,
    QLinearGradient, QRadialGradient, QPolygonF, QIcon,
)
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QLabel, QPushButton, QLineEdit,
    QCheckBox, QHBoxLayout, QVBoxLayout, QStackedWidget, QFileDialog,
    QFrame, QMessageBox,
)

# ── Boyutlar ──────────────────────────────────────────────────────────────────
CARD_W, CARD_H = 880, 520
LEFT_W = 320
RADIUS = 14

# ── Renkler ───────────────────────────────────────────────────────────────────
# Sol panel: koyu slate (login'in lacivertinden tamamen farklı)
SLATE_1 = "#0F172A"
SLATE_2 = "#1E293B"
SLATE_3 = "#334155"

ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
DANGER = "#DC2626"
DANGER_HOVER = "#B91C1C"
GREEN = "#10B981"

WHITE = "#FFFFFF"
GHOST = "#F8FAFC"
BORDER = "#E2E8F0"

INK = "#0F172A"
INK_SOFT = "#475569"
INK_FAINT = "#94A3B8"

APP_NAME = "Chenkron"
APP_VERSION = "5.3.7"
APP_ID = "{8B4F2C91-5E6D-4A77-9C3B-CH3NKR0N2026}"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Vektör ikon motoru ────────────────────────────────────────────────────────
try:
    import ui_icons as _ui
except ImportError:
    _ui = None

_IC = {}

def _px(name, sz=16, col="#FFFFFF", dpr=2.0):
    k = (name, sz, col, dpr)
    if k in _IC:
        return _IC[k]
    if _ui:
        try:
            px = _ui.pixmap(name, sz, col, dpr)
            _IC[k] = px
            return px
        except Exception:
            pass
    px = QPixmap(int(sz * dpr), int(sz * dpr))
    px.setDevicePixelRatio(dpr)
    px.fill(Qt.transparent)
    _IC[k] = px
    return px

def _icon(name, sz=16, col="#FFFFFF"):
    return QIcon(_px(name, sz, col))


# ── Checkbox checkmark asset ──────────────────────────────────────────────────
_CHK_PATH = None

def _chk_asset():
    global _CHK_PATH
    if _CHK_PATH and os.path.exists(_CHK_PATH):
        return _CHK_PATH.replace("\\", "/")
    d = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "chk_w.png")
    if not os.path.exists(p):
        px = QPixmap(18, 18)
        px.fill(Qt.transparent)
        pt = QPainter(px)
        pt.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(WHITE), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        pt.setPen(pen)
        path = QPainterPath()
        path.moveTo(4, 9.2); path.lineTo(7.6, 13); path.lineTo(14, 5)
        pt.drawPath(path)
        pt.end()
        px.save(p)
    _CHK_PATH = p
    return p.replace("\\", "/")


def _cb_css():
    ck = _chk_asset()
    return f"""
        QCheckBox {{ color:{INK}; font-size:13px; spacing:10px; background:transparent; }}
        QCheckBox:hover {{ color:{ACCENT}; }}
        QCheckBox::indicator {{ width:18px; height:18px; border-radius:5px;
            border:1.5px solid #CBD5E1; background:{WHITE}; }}
        QCheckBox::indicator:hover {{ border-color:{ACCENT}; }}
        QCheckBox::indicator:checked {{ background:{ACCENT}; border-color:{ACCENT};
            image:url("{ck}"); }}
    """


# ── Kurulum tespiti ───────────────────────────────────────────────────────────
def _default_dir():
    """Kullanıcının kendi klasörü — Program Files DEĞİL.

    İki sebep var. Birincisi: buraya kurmak yönetici hakkı istemez, yani
    kurulum sırasında hiç UAC penceresi çıkmaz. İkincisi ve asıl önemlisi:
    program kendi klasörüne yazabildiği için otomatik güncellemenin son
    adımı (yeni sürümü yerine koyma) da sessizce yapılabilir. Program
    Files'a kurulsaydı her güncellemede kullanıcıya bir kez daha UAC
    sorulacak, onaylamayan kullanıcı güncellemeyi hiç alamayacaktı.
    """
    base = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base, "Programs", APP_NAME)

def _detect():
    """Zaten kurulu bir Chenkron var mı? Eski sürümler Program Files'a
    kurulmuş olabilir, o yüzden oralara da bakılıyor: bulunursa onarım ve
    kaldırma doğru klasör üzerinde çalışır."""
    for d in [_default_dir(),
              os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), APP_NAME),
              os.path.join(os.environ.get("ProgramFiles(x86)", ""), APP_NAME)]:
        if d and os.path.exists(os.path.join(d, "Chenkron.exe")):
            return d
    return None


def _payload_zip():
    """Paketlenmiş installer'ın içindeki program arşivi, yoksa None.

    Program KLASÖR olarak değil, tek bir zip olarak gömülüyor. Sebebi
    somut: PyInstaller tek-dosya modunda gömülü ne varsa çalışmadan önce
    geçici klasöre açar. Klasör olarak gömseydik 4000'den fazla dosya
    önce temp'e, sonra hedefe kopyalanacaktı — kullanıcı bir dakika
    boyunca ilerleme çubuğu kıpırdamadan bekleyecekti. Tek zip'te bu
    bekleme birkaç saniyeye iniyor ve asıl açma işlemi doğrudan hedefe,
    ilerleme göstererek yapılıyor.
    """
    if not getattr(sys, "frozen", False):
        return None
    p = os.path.join(getattr(sys, "_MEIPASS", BASE_DIR), "payload.zip")
    return p if os.path.exists(p) else None


def _payload_dir():
    """Kaynaktan çalıştırıldığında (geliştirme) kullanılan kaynak klasör."""
    src = os.path.join(BASE_DIR, "dist", "Chenkron")
    return src if os.path.isdir(src) else BASE_DIR


# ══════════════════════════════════════════════════════════════════════════════
#  Worker Thread
# ══════════════════════════════════════════════════════════════════════════════
class _Worker(QThread):
    tick = Signal(int, str)
    done = Signal(bool, str)

    def __init__(self, mode, path, opts):
        super().__init__()
        self.mode, self.path, self.opts = mode, path, opts

    def run(self):
        try:
            {"install": self._install, "repair": self._repair,
             "uninstall": self._uninstall}[self.mode]()
        except Exception as e:
            self.done.emit(False, str(e))

    # --- install ---
    def _install(self):
        self.tick.emit(5, "Hedef klasör hazırlanıyor...")
        os.makedirs(self.path, exist_ok=True)
        time.sleep(.3)

        self.tick.emit(15, "Dosyalar kopyalanıyor...")
        zip_path = _payload_zip()
        if zip_path:
            self._extract(zip_path, 15, 65)
        else:
            src = _payload_dir()
            if os.path.exists(src) and src != self.path:
                items = os.listdir(src)
                for i, name in enumerate(items):
                    s, d = os.path.join(src, name), os.path.join(self.path, name)
                    if os.path.isdir(s):
                        if os.path.exists(d): shutil.rmtree(d, True)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                    self.tick.emit(15 + int(50 * (i+1) / max(1, len(items))),
                                   f"Aktarılıyor: {name}")

        self.tick.emit(70, "C++ motor doğrulanıyor...")
        time.sleep(.4)
        self.tick.emit(85, "Kısayollar oluşturuluyor...")
        exe = os.path.join(self.path, "Chenkron.exe")
        if self.opts.get("desktop"): self._shortcut(exe, "desktop")
        if self.opts.get("start_menu"): self._shortcut(exe, "startmenu")
        self.tick.emit(95, "Kayıt defteri güncelleniyor...")
        self._reg(exe)
        time.sleep(.2)
        self.tick.emit(100, "Kurulum tamamlandı.")
        self.done.emit(True, "Chenkron başarıyla kuruldu.")

    # --- repair ---
    def _repair(self):
        self.tick.emit(10, "Dosyalar taranıyor...")
        time.sleep(.4)
        if not os.path.exists(self.path):
            self.done.emit(False, f"Klasör bulunamadı: {self.path}"); return
        self.tick.emit(30, "Bileşenler yenileniyor...")
        zip_path = _payload_zip()
        if zip_path:
            # Onarım da kurulumun aynısı: eksik ya da bozulmuş ne varsa
            # arşivdeki sağlam haliyle üzerine yazılır. Kullanıcı verisi
            # program klasöründe değil ~/.chenki_akademi altında durduğu
            # için burada kaybolacak bir şey yok.
            self._extract(zip_path, 30, 65)
        else:
            src = _payload_dir()
            if os.path.exists(src):
                for f in os.listdir(src):
                    if f.endswith((".dll", ".exe")) or f == "_internal":
                        s = os.path.join(src, f)
                        d = os.path.join(self.path, f)
                        try:
                            if os.path.isdir(s): shutil.copytree(s, d, dirs_exist_ok=True)
                            else: shutil.copy2(s, d)
                        except Exception: pass
        time.sleep(.3)
        self.tick.emit(70, "Önbellek temizleniyor...")
        pc = os.path.join(self.path, "_internal", "__pycache__")
        if os.path.exists(pc): shutil.rmtree(pc, True)
        time.sleep(.3)
        self.tick.emit(90, "Kısayollar onarılıyor...")
        exe = os.path.join(self.path, "Chenkron.exe")
        self._shortcut(exe, "desktop"); self._reg(exe)
        self.tick.emit(100, "Onarım tamamlandı.")
        self.done.emit(True, "Bileşenler doğrulandı ve onarıldı.")

    # --- uninstall ---
    def _uninstall(self):
        self.tick.emit(15, "Kısayollar temizleniyor...")
        self._rm_shortcuts(); self._unreg()
        time.sleep(.3)
        self.tick.emit(50, "Program dosyaları siliniyor...")
        if os.path.exists(self.path): shutil.rmtree(self.path, True)
        time.sleep(.3)
        if not self.opts.get("keep_data", True):
            self.tick.emit(80, "Kullanıcı verileri siliniyor...")
            ud = os.path.join(os.path.expanduser("~"), ".chenki_akademi")
            if os.path.exists(ud): shutil.rmtree(ud, True)
        self.tick.emit(100, "Kaldırma tamamlandı.")
        self.done.emit(True, "Chenkron kaldırıldı.")

    # --- helpers ---
    def _extract(self, zip_path, pct_from, pct_to):
        """Arşivi hedefe açar ve gerçek ilerleme bildirir.

        Dosya SAYISINA değil BOYUTUNA göre ilerliyor: 4000 dosyanın çoğu
        birkaç kilobayt, birkaçı yüz megabayt. Sayıya göre ilerleyen bir
        çubuk %90'a fırlayıp orada uzun uzun bekler ve donmuş görünür.
        """
        import zipfile

        with zipfile.ZipFile(zip_path) as z:
            members = z.infolist()
            total = sum(m.file_size for m in members) or 1
            done = 0
            span = pct_to - pct_from
            last = -1
            for m in members:
                z.extract(m, self.path)
                done += m.file_size
                pct = pct_from + int(span * done / total)
                if pct != last:
                    last = pct
                    self.tick.emit(pct, f"Aktarılıyor: {os.path.basename(m.filename)}")

    def _shortcut(self, exe, kind):
        try:
            if kind == "desktop":
                lnk = os.path.join(os.path.expanduser("~"), "Desktop", f"{APP_NAME}.lnk")
            else:
                d = os.path.join(os.environ.get("APPDATA",""), "Microsoft","Windows",
                                 "Start Menu","Programs", APP_NAME)
                os.makedirs(d, exist_ok=True)
                lnk = os.path.join(d, f"{APP_NAME}.lnk")
            ico = os.path.join(self.path, "icon.ico")
            if not os.path.exists(ico): ico = exe
            ps = (f'$ws=New-Object -ComObject WScript.Shell;'
                  f'$s=$ws.CreateShortcut("{lnk}");'
                  f'$s.TargetPath="{exe}";$s.WorkingDirectory="{self.path}";'
                  f'$s.IconLocation="{ico}";$s.Save()')
            subprocess.run(["powershell","-NoProfile","-Command",ps], check=False)
        except Exception: pass

    def _rm_shortcuts(self):
        try:
            lnk = os.path.join(os.path.expanduser("~"),"Desktop",f"{APP_NAME}.lnk")
            if os.path.exists(lnk): os.remove(lnk)
            sd = os.path.join(os.environ.get("APPDATA",""),"Microsoft","Windows",
                              "Start Menu","Programs",APP_NAME)
            if os.path.exists(sd): shutil.rmtree(sd, True)
        except Exception: pass

    def _reg(self, exe):
        try:
            import winreg
            kp = f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_ID}_is1"
            # Kaldiriciyi kurulum klasorune birak: Windows'un "Uygulamalar"
            # listesindeki Kaldir dugmesinin calistiracagi bir sey olmali.
            # UninstallString'siz bir girdi listede gorunur ama hicbir sey
            # yapmaz — kullanici programi kaldiramaz.
            uninst = ""
            if getattr(sys, "frozen", False):
                try:
                    uninst = os.path.join(self.path, "ChenkronKurulum.exe")
                    shutil.copy2(sys.executable, uninst)
                except Exception:
                    uninst = ""

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, kp) as k:
                values = [("DisplayName","Chenkron"),("DisplayVersion",APP_VERSION),
                          ("Publisher","Chenkron"),("InstallLocation",self.path),
                          ("DisplayIcon",exe),("NoModify","1"),("NoRepair","0")]
                if uninst:
                    values.append(("UninstallString", f'"{uninst}"'))
                for n,v in values:
                    winreg.SetValueEx(k, n, 0, winreg.REG_SZ, v)
        except Exception: pass

    def _unreg(self):
        try:
            import winreg
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER,
                f"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_ID}_is1")
        except Exception: pass


# ══════════════════════════════════════════════════════════════════════════════
#  Custom Installer Window
# ══════════════════════════════════════════════════════════════════════════════
class CustomInstallerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} Kurulum Yöneticisi")
        self.setFixedSize(CARD_W, CARD_H)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._drag = None
        existing = _detect()
        self.installed = bool(existing)
        # Kurulu klasor ile YENI kurulumun hedefi ayri tutuluyor.
        # Eskiden tek bir deger vardi ve makinede Program Files'a kurulmus
        # bir kopya varsa "Kurulum" sekmesi de oraya isaret ediyordu; yani
        # kullanici yonetici hakki isteyen, guncellemesi her seferinde UAC
        # soracak bir yere kurmaya devam ediyordu. Onarim/kaldirma bulunan
        # kopya uzerinde calisir, yeni kurulum ise kullanicinin kendi
        # klasorune gider.
        self.installed_dir = existing
        self.target = _default_dir()
        self.worker = None

        self._build()
        self._set_mode("repair" if self.installed else "install")

    # --- drag -----------------------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() == Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)
    def mouseReleaseEvent(self, _): self._drag = None

    # --- paint ----------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        card = QRectF(0, 0, CARD_W, CARD_H)

        clip = QPainterPath()
        clip.addRoundedRect(card, RADIUS, RADIUS)
        p.save()
        p.setClipPath(clip)

        # beyaz arka plan
        p.fillRect(card, QColor(WHITE))

        # sol panel: koyu slate gradyan — diagonal
        left = QRectF(0, 0, LEFT_W, CARD_H)
        g = QLinearGradient(left.topLeft(), left.bottomRight())
        g.setColorAt(0.0, QColor("#1E293B"))
        g.setColorAt(0.6, QColor("#0F172A"))
        g.setColorAt(1.0, QColor("#020617"))
        p.fillRect(left, g)

        # Ürünle bağlantılı dekorasyon: soyut ders blokları (stepped rectangles)
        # Login'deki timetable grid'den FARKLI — burada soyutlanmış,
        # kenardan taşan, yarı saydam dikdörtgenler kurulum sürecini simgeliyor
        p.setPen(Qt.NoPen)
        blocks = [
            # (x, y, w, h, alpha)
            (LEFT_W - 80, 60, 60, 28, 18),
            (LEFT_W - 120, 96, 100, 22, 12),
            (LEFT_W - 60, 126, 48, 32, 22),
            (LEFT_W - 140, 170, 80, 20, 10),
            (LEFT_W - 100, 198, 60, 26, 16),
            # sol alt köşe
            (20, CARD_H - 120, 50, 24, 14),
            (30, CARD_H - 88, 70, 20, 10),
            (15, CARD_H - 60, 40, 28, 18),
        ]
        for bx, by, bw, bh, ba in blocks:
            p.setBrush(QColor(255, 255, 255, ba))
            p.drawRoundedRect(QRectF(bx, by, bw, bh), 4, 4)

        # Tek accent blok
        p.setBrush(QColor(ACCENT))
        p.setOpacity(0.25)
        p.drawRoundedRect(QRectF(LEFT_W - 90, 134, 44, 26), 4, 4)
        p.setOpacity(1.0)

        p.restore()

        # sağ panel çerçeve
        p.save()
        p.setClipRect(QRectF(LEFT_W, -2, CARD_W - LEFT_W + 2, CARD_H + 4))
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(card.adjusted(.5,.5,-.5,-.5), RADIUS, RADIUS)
        p.restore()
        p.end()

    # --- build ----------------------------------------------------------------
    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(0)
        root.addWidget(self._left())
        root.addWidget(self._right(), 1)

    def _left(self):
        w = QWidget()
        w.setFixedWidth(LEFT_W)
        w.setAttribute(Qt.WA_TranslucentBackground)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 44, 36, 36)
        lay.setSpacing(0)

        # logo
        logo_lbl = QLabel()
        for path in [os.path.join(BASE_DIR, "chenkron_logo_white.png"),
                     os.path.join(BASE_DIR, "bk_icon.png")]:
            if os.path.exists(path):
                px = QPixmap(path).scaledToWidth(52, Qt.SmoothTransformation)
                logo_lbl.setPixmap(px)
                break
        lay.addWidget(logo_lbl)
        lay.addSpacing(16)

        name = QLabel(APP_NAME)
        name.setFont(QFont("Segoe UI", 20, QFont.Bold))
        name.setStyleSheet("color:#FFFFFF;")
        lay.addWidget(name)

        sub = QLabel("Kurulum Yöneticisi")
        sub.setFont(QFont("Segoe UI", 9.5))
        sub.setStyleSheet("color:#94A3B8;")  # hex, rgba DEĞİL
        lay.addWidget(sub)

        lay.addStretch()

        # alt: sürüm + copyright
        ver = QLabel(f"v{APP_VERSION}")
        ver.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
        ver.setStyleSheet("color:#64748B;")
        lay.addWidget(ver)
        lay.addSpacing(4)
        copy_lbl = QLabel("© Chenkron 2026")
        copy_lbl.setFont(QFont("Segoe UI", 8))
        copy_lbl.setStyleSheet("color:#475569;")
        lay.addWidget(copy_lbl)

        return w

    def _right(self):
        w = QWidget()
        w.setObjectName("R")
        w.setStyleSheet(f"#R {{ background:{WHITE}; }}")

        lay = QVBoxLayout(w)
        lay.setContentsMargins(32, 24, 32, 28)
        lay.setSpacing(0)

        # başlık + window butonları
        top = QHBoxLayout()
        self._header = QLabel("Yeni Kurulum")
        self._header.setFont(QFont("Segoe UI", 15, QFont.Bold))
        self._header.setStyleSheet(f"color:{INK};")
        top.addWidget(self._header)
        top.addStretch()

        for kind in ("min", "close"):
            b = QPushButton()
            b.setFixedSize(28, 28)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("border:none; background:transparent;")
            if kind == "min":
                b.setIcon(_icon("download", 13, INK_FAINT))
                b.clicked.connect(self.showMinimized)
            else:
                b.setIcon(_icon("cross", 13, INK_FAINT))
                b.clicked.connect(self.reject)
            b.setIconSize(QSize(13,13))
            top.addWidget(b)
        lay.addLayout(top)
        lay.addSpacing(18)

        # segment butonları — solid fill aktif durum
        seg_frame = QFrame()
        seg_frame.setFixedHeight(40)
        seg_frame.setStyleSheet(f"background:#F1F5F9; border-radius:10px;")
        seg = QHBoxLayout(seg_frame)
        seg.setContentsMargins(3, 3, 3, 3)
        seg.setSpacing(2)
        self._seg_btns = {}
        for mid, txt, ic in [("install","Kurulum","download"),
                              ("repair","Onarım","refresh"),
                              ("uninstall","Kaldırma","trash")]:
            b = QPushButton(f"  {txt}")
            b.setFixedHeight(34)
            b.setFont(QFont("Segoe UI", 9.5, QFont.DemiBold))
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(_icon(ic, 14, INK_FAINT))
            b.setIconSize(QSize(14,14))
            b.clicked.connect(lambda _, m=mid: self._set_mode(m))
            seg.addWidget(b)
            self._seg_btns[mid] = b
        lay.addWidget(seg_frame)
        lay.addSpacing(16)

        # sayfa yığını
        self._stack = QStackedWidget()
        self._stack.addWidget(self._pg_install())   # 0
        self._stack.addWidget(self._pg_repair())    # 1
        self._stack.addWidget(self._pg_uninstall()) # 2
        self._stack.addWidget(self._pg_progress())  # 3
        self._stack.addWidget(self._pg_done())      # 4
        lay.addWidget(self._stack, 1)

        return w

    # ── segment mode ──────────────────────────────────────────────────────────
    def _set_mode(self, m):
        self._mode = m
        idx = {"install":0, "repair":1, "uninstall":2}[m]
        self._stack.setCurrentIndex(idx)

        titles = {"install": "Yeni Kurulum",
                  "repair": "Onarım",
                  "uninstall": "Kaldırma"}
        self._header.setText(titles[m])

        ic_map = {"install":"download","repair":"refresh","uninstall":"trash"}
        for mid, b in self._seg_btns.items():
            active = mid == m
            if active:
                if mid == "uninstall":
                    bg, fg = DANGER, WHITE
                else:
                    bg, fg = WHITE, INK
                b.setIcon(_icon(ic_map[mid], 14, fg))
                b.setStyleSheet(f"""
                    QPushButton {{
                        background:{bg}; color:{fg};
                        border:none; border-radius:8px;
                        font-weight:700; padding:0 14px;
                    }}
                """)
            else:
                b.setIcon(_icon(ic_map[mid], 14, INK_FAINT))
                b.setStyleSheet(f"""
                    QPushButton {{
                        background:transparent; color:{INK_FAINT};
                        border:none; border-radius:8px;
                        font-weight:600; padding:0 14px;
                    }}
                    QPushButton:hover {{ color:{INK_SOFT}; background:rgba(255,255,255,.5); }}
                """)

    # ── install page ──────────────────────────────────────────────────────────
    def _pg_install(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(10)

        # yol seçimi
        lbl = QLabel("Kurulum dizini")
        lbl.setFont(QFont("Segoe UI", 8.5, QFont.DemiBold))
        lbl.setStyleSheet(f"color:{INK_SOFT};")
        lay.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(6)
        self._path_edit = QLineEdit(self.target)
        self._path_edit.setFixedHeight(36)
        self._path_edit.setFont(QFont("Segoe UI", 9))
        self._path_edit.setStyleSheet(f"""
            QLineEdit {{ background:{WHITE}; border:1.5px solid {BORDER};
                border-radius:8px; padding:0 10px; color:{INK}; }}
            QLineEdit:focus {{ border-color:{ACCENT}; }}
        """)
        row.addWidget(self._path_edit, 1)

        bb = QPushButton("Gözat")
        bb.setFixedSize(64, 36)
        bb.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        bb.setCursor(Qt.PointingHandCursor)
        bb.setStyleSheet(f"""
            QPushButton {{ background:{GHOST}; color:{INK_SOFT}; border:1px solid {BORDER};
                border-radius:8px; }}
            QPushButton:hover {{ background:#F1F5F9; color:{INK}; }}
        """)
        bb.clicked.connect(self._browse)
        row.addWidget(bb)
        lay.addLayout(row)

        lay.addSpacing(4)

        # seçenekler
        css = _cb_css()
        self._ck_desk = QCheckBox("Masaüstü kısayolu")
        self._ck_desk.setChecked(True); self._ck_desk.setCursor(Qt.PointingHandCursor)
        self._ck_desk.setStyleSheet(css)
        lay.addWidget(self._ck_desk)

        self._ck_start = QCheckBox("Başlat Menüsü kısayolu")
        self._ck_start.setChecked(True); self._ck_start.setCursor(Qt.PointingHandCursor)
        self._ck_start.setStyleSheet(css)
        lay.addWidget(self._ck_start)

        self._ck_launch = QCheckBox("Kurulumdan sonra başlat")
        self._ck_launch.setChecked(True); self._ck_launch.setCursor(Qt.PointingHandCursor)
        self._ck_launch.setStyleSheet(css)
        lay.addWidget(self._ck_launch)

        lay.addStretch()

        btn = self._action_btn("Kur", "download")
        btn.clicked.connect(self._do_install)
        lay.addWidget(btn)
        return pg

    # ── repair page ───────────────────────────────────────────────────────────
    def _pg_repair(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(10)

        # bilgi kartı
        card = QFrame()
        card.setStyleSheet(f"background:{GHOST}; border:1px solid {BORDER}; border-radius:10px;")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(_px("gear", 20, ACCENT))
        cl.addWidget(ic)
        info = QLabel(f"Kurulu dizin: {self.installed_dir or self.target}")
        info.setFont(QFont("Segoe UI", 9))
        info.setStyleSheet(f"color:{INK_SOFT}; border:none;")
        info.setWordWrap(True)
        cl.addWidget(info, 1)
        lay.addWidget(card)

        css = _cb_css()
        self._ck_dll = QCheckBox("C++ Motor ve DLL'leri yenile")
        self._ck_dll.setChecked(True); self._ck_dll.setCursor(Qt.PointingHandCursor)
        self._ck_dll.setStyleSheet(css)
        lay.addWidget(self._ck_dll)

        self._ck_shorts = QCheckBox("Kısayolları yeniden oluştur")
        self._ck_shorts.setChecked(True); self._ck_shorts.setCursor(Qt.PointingHandCursor)
        self._ck_shorts.setStyleSheet(css)
        lay.addWidget(self._ck_shorts)

        self._ck_cache = QCheckBox("Önbelleği temizle")
        self._ck_cache.setChecked(True); self._ck_cache.setCursor(Qt.PointingHandCursor)
        self._ck_cache.setStyleSheet(css)
        lay.addWidget(self._ck_cache)

        # koruma notu
        nr = QHBoxLayout()
        nr.setSpacing(6)
        ni = QLabel()
        ni.setPixmap(_px("check", 12, GREEN))
        nr.addWidget(ni)
        nl = QLabel("Çizelge verileriniz korunur.")
        nl.setFont(QFont("Segoe UI", 8.5, QFont.DemiBold))
        nl.setStyleSheet(f"color:{GREEN};")
        nr.addWidget(nl)
        nr.addStretch()
        lay.addLayout(nr)

        lay.addStretch()

        btn = self._action_btn("Onar", "refresh")
        btn.clicked.connect(self._do_repair)
        lay.addWidget(btn)
        return pg

    # ── uninstall page ────────────────────────────────────────────────────────
    def _pg_uninstall(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(10)

        # uyarı kartı
        card = QFrame()
        card.setStyleSheet("background:#FEF2F2; border:1px solid #FECACA; border-radius:10px;")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(_px("warning", 20, DANGER))
        cl.addWidget(ic)
        info = QLabel("Program dosyaları ve kısayollar silinecektir.")
        info.setFont(QFont("Segoe UI", 9))
        info.setStyleSheet("color:#991B1B; border:none;")
        info.setWordWrap(True)
        cl.addWidget(info, 1)
        lay.addWidget(card)

        css = _cb_css()
        self._ck_keep = QCheckBox("Çizelge verilerimi koru")
        self._ck_keep.setChecked(True); self._ck_keep.setCursor(Qt.PointingHandCursor)
        self._ck_keep.setStyleSheet(css)
        lay.addWidget(self._ck_keep)

        lay.addStretch()

        btn = self._action_btn("Kaldır", "trash", danger=True)
        btn.clicked.connect(self._do_uninstall)
        lay.addWidget(btn)
        return pg

    # ── progress page ─────────────────────────────────────────────────────────
    def _pg_progress(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(0, 24, 0, 0)
        lay.setSpacing(12)

        self._p_title = QLabel("İşlem devam ediyor...")
        self._p_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._p_title.setStyleSheet(f"color:{INK};")
        lay.addWidget(self._p_title)

        self._p_msg = QLabel("Hazırlanıyor...")
        self._p_msg.setFont(QFont("Segoe UI", 9))
        self._p_msg.setStyleSheet(f"color:{INK_SOFT};")
        lay.addWidget(self._p_msg)

        bg = QFrame()
        bg.setFixedHeight(8)
        bg.setStyleSheet(f"background:#E2E8F0; border-radius:4px;")
        bl = QHBoxLayout(bg)
        bl.setContentsMargins(0,0,0,0)
        self._bar = QFrame()
        self._bar.setFixedHeight(8)
        self._bar.setFixedWidth(0)
        self._bar.setStyleSheet(f"background:{ACCENT}; border-radius:4px;")
        bl.addWidget(self._bar, 0, Qt.AlignLeft)
        bl.addStretch()
        lay.addWidget(bg)

        self._p_pct = QLabel("0%")
        self._p_pct.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self._p_pct.setStyleSheet(f"color:{ACCENT};")
        self._p_pct.setAlignment(Qt.AlignRight)
        lay.addWidget(self._p_pct)

        lay.addStretch()
        return pg

    # ── done page ─────────────────────────────────────────────────────────────
    def _pg_done(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignCenter)

        self._d_ico = QLabel()
        self._d_ico.setAlignment(Qt.AlignCenter)
        self._d_ico.setPixmap(_px("check_circle", 48, GREEN))
        lay.addWidget(self._d_ico, 0, Qt.AlignCenter)

        self._d_title = QLabel("Tamamlandı")
        self._d_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self._d_title.setStyleSheet(f"color:{INK};")
        self._d_title.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._d_title)

        self._d_msg = QLabel("")
        self._d_msg.setFont(QFont("Segoe UI", 9.5))
        self._d_msg.setStyleSheet(f"color:{INK_SOFT};")
        self._d_msg.setAlignment(Qt.AlignCenter)
        self._d_msg.setWordWrap(True)
        lay.addWidget(self._d_msg)

        lay.addSpacing(12)

        row = QHBoxLayout()
        row.addStretch()

        self._d_close = QPushButton("Kapat")
        self._d_close.setFixedSize(90, 38)
        self._d_close.setFont(QFont("Segoe UI", 9.5, QFont.DemiBold))
        self._d_close.setCursor(Qt.PointingHandCursor)
        self._d_close.setStyleSheet(f"""
            QPushButton {{ background:{WHITE}; color:{INK_SOFT}; border:1.5px solid {BORDER};
                border-radius:19px; }}
            QPushButton:hover {{ background:{GHOST}; color:{INK}; }}
        """)
        self._d_close.clicked.connect(self.accept)
        row.addWidget(self._d_close)

        self._d_launch = QPushButton("  Başlat")
        self._d_launch.setFixedSize(110, 38)
        self._d_launch.setFont(QFont("Segoe UI", 9.5, QFont.Bold))
        self._d_launch.setCursor(Qt.PointingHandCursor)
        self._d_launch.setIcon(_icon("arrow_right", 14, WHITE))
        self._d_launch.setIconSize(QSize(14,14))
        self._d_launch.setStyleSheet(f"""
            QPushButton {{ background:{ACCENT}; color:{WHITE}; border:none; border-radius:19px; }}
            QPushButton:hover {{ background:{ACCENT_HOVER}; }}
        """)
        self._d_launch.clicked.connect(self._launch)
        row.addWidget(self._d_launch)
        row.addStretch()
        lay.addLayout(row)
        return pg

    # ── helpers ───────────────────────────────────────────────────────────────
    def _action_btn(self, text, ic_name, danger=False):
        b = QPushButton(f"  {text}")
        b.setFixedHeight(42)
        b.setFont(QFont("Segoe UI", 11, QFont.Bold))
        b.setCursor(Qt.PointingHandCursor)
        b.setIcon(_icon(ic_name, 16, WHITE))
        b.setIconSize(QSize(16,16))
        bg = DANGER if danger else ACCENT
        bgh = DANGER_HOVER if danger else ACCENT_HOVER
        b.setStyleSheet(f"""
            QPushButton {{ background:{bg}; color:{WHITE}; border:none; border-radius:21px; }}
            QPushButton:hover {{ background:{bgh}; }}
        """)
        return b

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Kurulum Klasörü", self.target)
        if d:
            self.target = d
            self._path_edit.setText(d)

    # --- actions ---
    def _do_install(self):
        t = self._path_edit.text().strip()
        if not t:
            QMessageBox.warning(self, "Uyarı", "Kurulum dizini belirtin."); return
        self.target = t
        self._run("install", "Kuruluyor...", {
            "desktop": self._ck_desk.isChecked(),
            "start_menu": self._ck_start.isChecked(),
            "launch": self._ck_launch.isChecked()})

    def _do_repair(self):
        self.target = self.installed_dir or self.target
        self._run("repair", "Onarılıyor...", {
            "engine": self._ck_dll.isChecked(),
            "shortcuts": self._ck_shorts.isChecked(),
            "cache": self._ck_cache.isChecked()})

    def _do_uninstall(self):
        if QMessageBox.question(self, "Onay", "Chenkron kaldırılsın mı?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.target = self.installed_dir or self.target
        self._run("uninstall", "Kaldırılıyor...", {"keep_data": self._ck_keep.isChecked()})

    def _run(self, mode, title, opts):
        for b in self._seg_btns.values(): b.setEnabled(False)
        self._p_title.setText(title)
        self._p_msg.setText("Hazırlanıyor...")
        self._bar.setFixedWidth(0)
        self._p_pct.setText("0%")
        self._stack.setCurrentIndex(3)

        self.worker = _Worker(mode, self.target, opts)
        self.worker.tick.connect(self._on_tick)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _on_tick(self, pct, msg):
        self._p_msg.setText(msg)
        self._p_pct.setText(f"{pct}%")
        self._bar.setFixedWidth(max(4, int(pct / 100 * 480)))

    def _on_done(self, ok, msg):
        self._stack.setCurrentIndex(4)
        for b in self._seg_btns.values(): b.setEnabled(True)
        mode = self.worker.mode if self.worker else "install"
        if ok:
            if mode == "uninstall":
                self._d_ico.setPixmap(_px("check_circle", 48, INK_FAINT))
                self._d_title.setText("Kaldırıldı")
                self._d_launch.setVisible(False)
            else:
                self._d_ico.setPixmap(_px("check_circle", 48, GREEN))
                self._d_title.setText("Tamamlandı")
                self._d_launch.setVisible(True)
            self._d_msg.setText(msg)
        else:
            self._d_ico.setPixmap(_px("warning", 48, DANGER))
            self._d_title.setText("Hata")
            self._d_msg.setText(msg)
            self._d_launch.setVisible(False)

    def _launch(self):
        exe = os.path.join(self.target, "Chenkron.exe")
        if os.path.exists(exe):
            try: subprocess.Popen([exe], cwd=self.target)
            except Exception: pass
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = app.palette()
    pal.setColor(pal.ColorRole.WindowText, QColor(INK))
    pal.setColor(pal.ColorRole.Text, QColor(INK))
    app.setPalette(pal)

    win = CustomInstallerWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
