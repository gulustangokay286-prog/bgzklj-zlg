"""Sohbet döngüsü: soru -> model -> araçlar (GUI'de) -> cevap.

Model ağ üzerinden konuşur, bu yüzden ayrı iş parçacığında çalışır. Araçlar
ise uygulamanın verisine ve pencerelerine dokunur; onlar GUI iş parçacığında
koşmak ZORUNDADIR. Köprü: iş parçacığı `tool_requested` sinyalini yayar, GUI
tarafı aracı çalıştırıp `deliver_tool_result` ile sonucu geri verir, iş
parçacığı o sırada bekler. Sıralı işler ("pazartesiyi aç, sonra planla")
böylece doğru sırayla ve birbirini bekleyerek yürür.
"""
import threading

from PySide6.QtCore import QObject, Signal, QThread

from .gemini import (GeminiClient, GeminiError, user_turn, model_turn,
                     tool_results_turn, compact)
from . import tools as T

MAX_ROUNDS = 8          # bir soru için en fazla model turu (araç zinciri)
HISTORY_TURNS = 12      # geçmişte tutulan konuşma turu


class AssistantAgent(QObject):
    thinking = Signal(bool)                 # meşgul göstergesi
    tool_started = Signal(str, dict)        # ad, argümanlar
    tool_finished = Signal(str, dict)       # ad, sonuç
    answered = Signal(str)                  # nihai metin
    failed = Signal(str)
    tool_requested = Signal(str, dict)      # GUI: aracı çalıştır, sonucu ver

    def __init__(self, actions, client=None, parent=None):
        super().__init__(parent)
        self.actions = actions
        self.client = client or GeminiClient()
        self.history = []
        self._thread = None
        self._result_event = threading.Event()
        self._result = None
        self._cancel = False
        self.tool_requested.connect(self._run_tool_on_gui)

    # ── GUI tarafı ────────────────────────────────────────────────────────
    def _run_tool_on_gui(self, name, args):
        try:
            result = self.actions.execute(name, args)
        except Exception as exc:
            result = {"ok": False, "message": f"Hata: {exc}"}
        self.deliver_tool_result(result)

    def deliver_tool_result(self, result):
        self._result = result
        self._result_event.set()

    def busy(self):
        return self._thread is not None and self._thread.isRunning()

    def cancel(self):
        self._cancel = True
        self._result_event.set()

    def ask(self, text):
        text = (text or "").strip()
        if not text or self.busy():
            return False
        self._cancel = False
        self.history.append(user_turn(text))
        self._trim()

        class _Worker(QThread):
            def __init__(w, agent):
                super().__init__()
                w.agent = agent

            def run(w):
                w.agent._loop()

        self._thread = _Worker(self)
        self._thread.finished.connect(lambda: self.thinking.emit(False))
        self.thinking.emit(True)
        self._thread.start()
        return True

    # ── iş parçacığı tarafı ───────────────────────────────────────────────
    def _loop(self):
        try:
            for _ in range(MAX_ROUNDS):
                if self._cancel:
                    return
                reply = self.client.generate(self.history, system=T.SYSTEM, tools=T.TOOLS)
                self.history.append(model_turn(reply.parts))
                calls = reply.calls
                if not calls:
                    self.answered.emit(reply.text or "Tamam.")
                    return
                results = []
                for call_id, name, args in calls:
                    if self._cancel:
                        return
                    self.tool_started.emit(name, args)
                    self._result_event.clear()
                    self._result = None
                    self.tool_requested.emit(name, args)
                    while not self._result_event.wait(0.25):
                        if self._cancel:
                            return
                    result = self._result if isinstance(self._result, dict) else {"ok": False}
                    self.tool_finished.emit(name, result)
                    results.append((call_id, name, compact(result)))
                self.history.append(tool_results_turn(results))
            self.answered.emit("İşlemler yapıldı.")
        except GeminiError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"Beklenmeyen hata: {exc}")

    def _trim(self):
        # Geçmiş sınırlı tutulur; araç turları çiftler hâlinde gider.
        if len(self.history) > HISTORY_TURNS * 2:
            self.history = self.history[-HISTORY_TURNS * 2:]
            # İlk kayıt model turu ya da araç cevabı olmasın.
            while self.history and (self.history[0].get("role") != "user"
                                    or "functionResponse" in self.history[0]["parts"][0]):
                self.history.pop(0)
