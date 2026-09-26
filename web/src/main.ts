// Deneme arayüzü: .roz yükle, planla, sonucu sınıf sınıf gör.
// Motorun tamamı engine.worker.ts içinde; bu sayfa yalnızca gösterir.
import { getMatrix, gridDimensions } from './engine/data.ts';

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
let data: any = null;
let worker: Worker | null = null;
let result: any = null;

$('env').textContent = `${navigator.hardwareConcurrency || '?'} çekirdek · `
  + (crossOriginIsolated ? 'CP-SAT çok iş parçacıklı' : 'CP-SAT tek iş parçacıklı (COOP/COEP yok)');

const SAMPLES = import.meta.env.DEV ? ['birey_v161', 'bogazici_v227', 'bogazici_v229'] : [];
for (const s of SAMPLES) {
  const b = document.createElement('button');
  b.textContent = s;
  b.onclick = () => loadUrl(`/samples/${s}.roz`, s);
  $('samples').append(b);
}

function setData(d: any, name: string) {
  data = d;
  const n = (d.atamalar ?? []).length, c = (d.siniflar ?? []).length;
  const kilit = (d.grid_placements ?? []).filter((p: any) => p?.locked || p?.is_locked).length;
  $('loaded').textContent = `${name} · ${c} sınıf · ${n} atama · ${kilit} kilitli kayıt`;
  ($('run') as HTMLButtonElement).disabled = false;
}

async function loadUrl(url: string, name: string) {
  const r = await fetch(url);
  setData(await r.json(), name);
}

$<HTMLInputElement>('file').onchange = async (e) => {
  const f = (e.target as HTMLInputElement).files?.[0];
  if (f) setData(JSON.parse(await f.text()), f.name);
};

function prepare(mode: string) {
  const d = structuredClone(data);
  const gp = (d.grid_placements ?? []).filter((p: any) => p && typeof p === 'object');
  if (mode === 'all') { d.grid_placements = []; d.auto_schedule_results = []; }
  else if (mode === 'locked') d.grid_placements = gp.filter((p: any) => p.locked || p.is_locked);
  d.yerlesim = {}; d.loose_unplaced_cards = []; d.manual_unplaced_cards = [];
  return d;
}

function show(id: string, on: boolean) { $(id).hidden = !on; }

function start(unlock = false) {
  const mode = (document.querySelector('input[name=mode]:checked') as HTMLInputElement).value;
  const d = prepare(mode);
  worker?.terminate();
  worker = new Worker(new URL('./workers/engine.worker.ts', import.meta.url), { type: 'module' });
  worker.onmessage = onMessage;
  worker.onerror = (e) => fail(e.message);
  ['result', 'ask', 'conflict'].forEach((id) => show(id, false));
  show('progress', true);
  $('status').textContent = 'Başlatılıyor…';
  $('hours').textContent = '…';
  ($('run') as HTMLButtonElement).disabled = true;
  show('stop', true);
  worker.postMessage({ type: 'run', data: d, unlock });
}

let best = 0;
function onMessage(e: MessageEvent) {
  const m = e.data;
  if (m.type === 'status') $('status').textContent = m.text;
  else if (m.type === 'progress') {
    best = Math.max(best, m.placed);
    $('hours').textContent = `${m.placed}/${m.total} saat`;
    $('elapsed').textContent = `${m.t.toFixed(1)} sn`;
    $('barfill').style.width = `${Math.round((100 * m.placed) / Math.max(1, m.total))}%`;
  } else if (m.type === 'ask') {
    const i = m.info;
    $('asktext').textContent = `${i.saat}/${i.toplam} saat yerleşti, ${Math.round(i.gecen)} sn geçti.`
      + (i.ust !== null && i.ust < i.toplam ? ` Bu kurallarla en fazla ${i.ust} saat mümkün.` : '')
      + ' Bir tur daha arayabilirim ya da bu hâliyle bitirebilirim.';
    show('ask', true);
  } else if (m.type === 'conflict') {
    $('conflictlist').innerHTML = '';
    for (const t of m.items) { const li = document.createElement('li'); li.textContent = t; $('conflictlist').append(li); }
    show('conflict', true);
    finish();
  } else if (m.type === 'error') fail(m.message);
  else if (m.type === 'done') { result = m.result; render(m.t); finish(); }
}

function finish() {
  ($('run') as HTMLButtonElement).disabled = !data;
  show('stop', false);
  show('ask', false);
}

function fail(msg: string) {
  $('status').textContent = 'Hata: ' + msg;
  finish();
}

$('run').onclick = () => start(false);
$('unlock').onclick = () => start(true);
$('cancelconflict').onclick = () => show('conflict', false);
$('stop').onclick = () => { worker?.postMessage({ type: 'cancel' }); $('status').textContent = 'Durduruluyor, en iyi çözüm alınıyor…'; };
$('askwait').onclick = () => { worker?.postMessage({ type: 'answer', devam: true }); show('ask', false); };
$('askstop').onclick = () => { worker?.postMessage({ type: 'answer', devam: false }); show('ask', false); };

function render(t: number) {
  const r = result;
  show('result', true);
  $('barfill').style.width = `${Math.round((100 * r.placed_hours) / Math.max(1, r.total_assigned_hours))}%`;
  $('hours').textContent = `${r.placed_hours}/${r.total_assigned_hours} saat`;
  $('status').textContent = `Bitti · durum: ${r.status}`;
  $('summary').innerHTML = `<span class="${r.complete ? 'ok' : 'bad'}">${r.placed_hours}/${r.total_assigned_hours} saat</span>`
    + ` · ${t.toFixed(1)} sn · ${r.complete ? 'tam çizelge, sert kural ihlali yok' : 'eksik — sebebi raporda'}`;
  $('unplaced').innerHTML = '';
  for (const u of r.unplaced_summary) {
    const div = document.createElement('div');
    div.className = 'unplaced';
    div.textContent = `Yerleşmedi: ${u.class} · ${u.subject} (${u.teacher}) — ${u.hours} saat`;
    $('unplaced').append(div);
  }
  $('warnings').innerHTML = '';
  for (const w of r.warnings) { const li = document.createElement('li'); li.textContent = w; $('warnings').append(li); }
  const sel = $<HTMLSelectElement>('cls');
  sel.innerHTML = '';
  for (const c of r.classes) { const o = document.createElement('option'); o.value = o.textContent = c; sel.append(o); }
  sel.onchange = () => drawGrid(sel.value);
  drawGrid(r.classes[0]);
}

function drawGrid(cls: string) {
  const r = result;
  const [D, P] = gridDimensions(data);
  const days: string[] = Array.isArray(data.settings?.days) && data.settings.days.length >= D
    ? data.settings.days.slice(0, D) : Array.from({ length: D }, (_, d) => `${d + 1}. gün`);
  const sinif = (data.siniflar ?? []).find((c: any) => (c.ad || c.name) === cls);
  const closed = sinif ? getMatrix(sinif, cls, data) : null;
  const cells = new Map<string, any>();
  for (const pl of r.schedule) {
    if ((pl.class_name || pl.class) !== cls) continue;
    for (let off = 0; off < (pl.duration || 1); off++) cells.set(`${pl.day},${pl.period + off}`, pl);
  }
  let html = '<table><thead><tr><th></th>' + days.map((d) => `<th>${d}</th>`).join('') + '</tr></thead><tbody>';
  for (let p = 0; p < P; p++) {
    html += `<tr><th>${p + 1}</th>`;
    for (let d = 0; d < D; d++) {
      const pl = cells.get(`${d},${p}`);
      const isClosed = closed ? closed[d][p] === 0 : false;
      if (pl) {
        const cls2 = pl.locked ? 'lock' : pl.is_split ? 'split' : 'on';
        html += `<td class="${cls2}${isClosed ? ' closed' : ''}"><span class="s">${esc(pl.subject_name || pl.subject)}</span><span class="t">${esc(pl.teacher_name || pl.teacher)}</span></td>`;
      } else html += `<td class="${isClosed ? 'closed' : ''}"></td>`;
    }
    html += '</tr>';
  }
  $('grid').innerHTML = html + '</tbody></table>';
}

function esc(s: unknown) {
  return String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));
}

const q = new URLSearchParams(location.search).get('ornek');
if (q && SAMPLES.includes(q)) loadUrl(`/samples/${q}.roz`, q);
