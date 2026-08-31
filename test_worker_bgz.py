import os
import sys
import json
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop

app = QApplication.instance() or QApplication(sys.argv)

import version_store
from auto_scheduler import AutoSchedulerWorker

slug = "bogazici_egitim_kurumlari"
active_vf = version_store.get_active_version(slug)
print(f"Testing AutoSchedulerWorker on {slug} (active: {active_vf})")

data_store = version_store.load_version(slug, active_vf)

worker = AutoSchedulerWorker(
    data_store, target_class=None,
    fill_empty=True, institution_slug=slug,
    use_vds=False, infinite_mode=True,
    ignore_other_institutions=False,
    independent_classes=False
)

loop = QEventLoop()
results = {}

def on_finished(res):
    results["res"] = res
    print(f"Worker finished_successfully! Placed: {res.get('placed_hours')} / {res.get('total_hours')}")
    print(f"Schedule items count: {len(res.get('schedule', []))}")
    print(f"Cross conflicts count: {len(res.get('cross_conflicts', []))}")
    print(f"Unplaced summary count: {len(res.get('unplaced_summary', []))}")
    loop.quit()

def on_failed(err):
    results["err"] = err
    print(f"Worker failed with error: {err}")
    loop.quit()

worker.finished_successfully.connect(on_finished)
worker.failed.connect(on_failed)
worker.start()

loop.exec()

print("Worker thread ended.")
if "res" in results:
    res = results["res"]
    schedule = res.get("schedule", [])
    print(f"Total schedule placements: {len(schedule)}")
    total_hours = sum(int(x.get("duration", 1) or 1) for x in schedule)
    print(f"Total hours in schedule: {total_hours}")
