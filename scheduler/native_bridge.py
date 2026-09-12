"""Build/load the native executable and stream legal incumbents to the UI."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time

_BUILD_LOCK = threading.Lock()


def native_binary():
    filename = 'chenkron-scheduler.exe' if os.name == 'nt' else 'chenkron-scheduler'
    bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent)) / 'scheduler' / 'native' / filename
    source = Path(__file__).parent / 'native' / 'search.cpp'
    if bundled.is_file() and (getattr(sys, 'frozen', False) or
                              bundled.stat().st_mtime >= source.stat().st_mtime):
        return bundled
    if getattr(sys, 'frozen', False):
        raise RuntimeError('Uygulama paketinde C++ planlama motoru eksik. Uygulamayı yeniden paketleyin.')
    source = Path(__file__).parent / 'native' / 'search.cpp'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:20]
    target = Path(tempfile.gettempdir()) / 'chenkron-native' / digest / filename
    with _BUILD_LOCK:
        if not target.is_file():
            compiler = shutil.which(os.environ.get('CXX', 'clang++')) or shutil.which('g++')
            if not compiler:
                raise RuntimeError('C++ motoru derlenmemiş; clang++ veya g++ gerekiyor.')
            target.parent.mkdir(parents=True, exist_ok=True)
            temp = target.with_name(filename+f'.{os.getpid()}.tmp')
            built = subprocess.run([compiler, '-std=c++17', '-O3', '-DNDEBUG', str(source), '-o', str(temp)],
                                   capture_output=True, text=True, timeout=60)
            if built.returncode:
                raise RuntimeError('C++ motoru derlenemedi: '+built.stderr[-2000:])
            temp.replace(target)
    return target


def search(problem, seconds, seed, upper_bound, progress=None, cancelled=None,
           input_path=None):
    deadline = time.monotonic() + max(0.0, seconds)
    binary = native_binary()
    best = None
    with tempfile.TemporaryDirectory(prefix='chenkron-solve-') as tmp:
        out, err = (Path(tmp)/name for name in ('output','error'))
        # Problem dosyası tohumdan bağımsızdır; hazır verilmişse yeniden
        # yazılmaz. v188'de dosya 4,5 MB ve her şerit için ayrı yazmak,
        # aramanın kendisinden pahalıya geliyordu.
        if input_path is None:
            inp = Path(tmp)/'input'
            with inp.open('w') as f:
                problem.write(f, max(0.0,seconds), seed & 0xffffffff, upper_bound)
        else:
            inp = Path(input_path)
        with inp.open('r') as stdin, out.open('w') as stdout, err.open('w') as stderr:
            proc = subprocess.Popen([str(binary), str(max(0.0, deadline-time.monotonic())),
                                     str(seed & 0x7fffffff)],
                                    stdin=stdin,stdout=stdout,stderr=stderr)
        cancel_sent = False
        stop_time = None
        def read_line(line):
            nonlocal best
            values=line.split()
            if not values or values[0] not in ('P','F'): return
            if len(values) != len(problem.world.cards)+5:
                raise RuntimeError('C++ motorundan eksik sonuç geldi')
            best = dict(hours=int(values[1]),steps=int(values[2]),restarts=int(values[3]),
                        soft_cost=int(values[4]),positions=list(map(int,values[5:])))
            if callable(progress): progress(best)
        try:
            with out.open() as reader:
                while proc.poll() is None:
                    for line in reader: read_line(line)
                    if callable(cancelled) and cancelled() and not cancel_sent:
                        proc.terminate();cancel_sent=True;stop_time=time.monotonic()
                    if stop_time is not None and time.monotonic()-stop_time>2:
                        proc.kill()
                    time.sleep(0.02)
                for line in reader: read_line(line)
            if proc.returncode and not cancel_sent:
                raise RuntimeError('C++ motoru başarısız: '+err.read_text()[-2000:])
            if best is None:
                best=dict(hours=0,steps=0,restarts=0,soft_cost=0,positions=[-1]*len(problem.world.cards))
            best['cancelled']=cancel_sent
            return best
        finally:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill();proc.wait()


def search_portfolio(problem, seconds, seeds, upper_bound, progress=None,
                     cancelled=None, workers=None):
    """Aynı problemi FARKLI TOHUMLARLA aynı anda arar; ilk tam sonucu alır.

    Tabu araması rastgele bir noktadan yürür ve yerel bir vadide takılabilir.
    Aynı tohumla daha uzun beklemek o vadiden çıkarmaz — başka bir tohumla
    baştan başlamak çıkarır. v188'de ölçtüğümüz şey tam buydu: aynı süreyle
    bir tohum 283'te kalırken başka bir tohum 285'i buluyordu.

    Tohumları sırayla denemek bu şansı süreye böler. Aynı anda denemek ise
    bölmez: C++ araması zaten ayrı bir süreçte koştuğu için sekiz çekirdekli
    bir makinede sekiz tohum aynı duvar saatinde ilerler. Böylece "hangi
    tohumu seçtiğim" sorusu sonucu belirlemekten çıkar.

    İlk tam çözüm bulunduğunda diğerleri durdurulur; tamamlanmış bir çizelgeyi
    iyileştirmeye çalışmak boşa zamandır.
    """
    import concurrent.futures
    import threading

    if workers is None:
        workers = max(1, min(len(seeds), (os.cpu_count() or 4)))
    found = threading.Event()
    lock = threading.Lock()
    best = {'rec': None}

    def stop_requested():
        return found.is_set() or bool(callable(cancelled) and cancelled())

    def run(seed, input_path=None):
        rec = search(problem, seconds, seed, upper_bound,
                     progress=progress, cancelled=stop_requested,
                     input_path=input_path)
        with lock:
            cur = best['rec']
            better = (cur is None or rec['hours'] > cur['hours']
                      or (rec['hours'] == cur['hours']
                          and rec['soft_cost'] < cur['soft_cost']))
            if better:
                best['rec'] = rec
        if rec['hours'] >= upper_bound:
            found.set()
        return rec

    # Bütün şeritler TEK bir problem dosyasını paylaşır; tohum komut satırından
    # verilir. Sekiz şeridin her biri için 4,5 MB'ı ayrı ayrı yazmak, sekiz
    # çekirdeği paralel çalıştırmakla kazanılanı geri veriyordu.
    with tempfile.TemporaryDirectory(prefix='chenkron-pool-') as shared:
        shared_input = Path(shared)/'input'
        with shared_input.open('w') as f:
            problem.write(f, max(0.0, seconds), 1, upper_bound)

        def run_shared(seed):
            return run(seed, str(shared_input))

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(run_shared, list(seeds)))

    rec = best['rec']
    if rec is None:
        rec = dict(hours=0, steps=0, restarts=0, soft_cost=0,
                   positions=[-1]*len(problem.world.cards))
    # Erken durdurma bizim kararımızdı; kullanıcı iptali değil.
    rec['cancelled'] = bool(callable(cancelled) and cancelled())
    return rec
