"""window_log.py — hangi pencere ne zaman açıldı, dosyaya yazar.

Ekranda beliren ama içeriği boyanmamış kara pencereler, hangi widget'ın
onları açtığını söylemiyor: ne başlıkları var ne içerikleri. Bu günlük o
soruyu cevaplıyor — her üst düzey pencere gösterildiğinde sınıfı,
başlığı, ölçüsü ve bayrakları bir dosyaya düşüyor.

Kayıt yeri: ~/.chenki_akademi/pencere_gunlugu.txt

Hiçbir şeyi değiştirmez, yalnızca gözlemler; sorun çözülünce install()
çağrısı kaldırılabilir.
"""
import os
import time

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QWidget

LOG_PATH = os.path.join(os.path.expanduser("~"), ".chenki_akademi",
                        "pencere_gunlugu.txt")
_installed = False


def _write(line):
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


class _WindowWatcher(QObject):
    def eventFilter(self, obj, ev):
        try:
            t = ev.type()
            if t in (QEvent.Show, QEvent.Hide, QEvent.Close) and isinstance(obj, QWidget):
                if obj.isWindow():
                    g = obj.frameGeometry()
                    flags = obj.windowFlags()
                    kind = {QEvent.Show: "AÇILDI", QEvent.Hide: "GİZLENDİ",
                            QEvent.Close: "KAPANDI"}[t]
                    _write(
                        f"{time.strftime('%H:%M:%S')} {kind:9} "
                        f"{type(obj).__name__:30} '{(obj.windowTitle() or '(başlıksız)')[:36]}' "
                        f"{g.width()}x{g.height()} @({g.x()},{g.y()}) "
                        f"frameless={bool(flags & Qt.FramelessWindowHint)} "
                        f"saydam={obj.testAttribute(Qt.WA_TranslucentBackground)} "
                        f"modal={obj.isModal()}")
        except Exception:
            pass
        return False


_watcher = None


def install(app):
    """Uygulamaya tak. İki kez çağrılsa da bir kez takılır."""
    global _installed, _watcher
    if _installed or app is None:
        return
    _watcher = _WindowWatcher()
    app.installEventFilter(_watcher)
    _installed = True
    _write("\n" + "=" * 70)
    _write(f"OTURUM BAŞLADI {time.strftime('%Y-%m-%d %H:%M:%S')}  pid={os.getpid()}")
    _write("=" * 70)
