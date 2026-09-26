// exporters.py karşılığı: dışa aktarılacak tabloları üretir ve .xlsx / .csv yazar.
// .xlsx için dış kütüphane yok: küçük bir ZIP (sıkıştırmasız) + OOXML yazıcısı.
import { bellTimes } from './print/reports.tsx';

const norm = (v: unknown) => String(v ?? '').split(/\s+/).filter(Boolean).join(' ').trim();
const int0 = (v: unknown) => { const n = Number(v); return Number.isFinite(n) ? Math.trunc(n) : 0; };

function gridDims(d: any): { days: string[]; periods: number } {
  const st = d.settings ?? {};
  let days: string[] = st.days;
  if (!Array.isArray(days) || !days.length) days = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'].slice(0, int0(st.day_count ?? d.gun_sayisi ?? 5) || 5);
  return { days: [...days], periods: int0(st.periods ?? d.ders_saati ?? 8) || 8 };
}

function periodLabels(d: any, periods: number): string[] {
  const t = bellTimes(d, periods, '-');
  return Array.from({ length: periods }, (_, p) => `${p + 1}. Ders\n${t[p]}`);
}

function index(d: any) {
  const byClass = new Map<string, any>(), byTeacher = new Map<string, any>(), byRoom = new Map<string, any>();
  for (const p of d.grid_placements ?? []) {
    if (!p || typeof p !== 'object') continue;
    const day = int0(p.day ?? p.col), st = int0(p.period ?? p.row), span = Math.max(1, int0(p.duration) || 1);
    const c = norm(p.class_name || p.class), t = norm(p.teacher_name || p.teacher), r = norm(p.room_name || p.room || p.derslik);
    for (let o = 0; o < span; o++) {
      const s = `${day}|${st + o}`;
      if (c) byClass.set(`${c}|${s}`, p);
      if (t) byTeacher.set(`${t}|${s}`, p);
      if (r) byRoom.set(`${r}|${s}`, p);
    }
  }
  return { byClass, byTeacher, byRoom };
}

function cellText(p: any, view: string): string {
  if (!p) return '';
  const s = norm(p.subject_name || p.subject), t = norm(p.teacher_name || p.teacher), c = norm(p.class_name || p.class), r = norm(p.room_name || p.room || p.derslik);
  const parts = view === 'classes' ? [s, t] : view === 'teachers' ? [s, c] : [s, c, t];
  if (r && view !== 'rooms') parts.push(r);
  return parts.filter(Boolean).join('\n');
}

type Table = [string[], (string | number)[][]];

function timetable(d: any, view: 'classes' | 'teachers' | 'rooms'): Table {
  const { days, periods } = gridDims(d);
  const labels = periodLabels(d, periods);
  const ix = index(d);
  const [list, idx, first] = view === 'teachers' ? [d.ogretmenler, ix.byTeacher, 'Öğretmen'] : view === 'rooms' ? [d.derslikler, ix.byRoom, 'Derslik'] : [d.siniflar, ix.byClass, 'Sınıf'];
  const ents = (list ?? []).filter((x: any) => x && typeof x === 'object').map((x: any) => norm(x.ad || x.name)).filter(Boolean) as string[];
  const headers = [first];
  for (const day of days) for (const l of labels) headers.push(`${day} ${l.split('\n')[0]}`);
  const rows = ents.map((e) => {
    const row: string[] = [e];
    for (let dd = 0; dd < days.length; dd++) for (let p = 0; p < periods; p++) row.push(cellText(idx.get(`${e}|${dd}|${p}`), view));
    return row;
  });
  return [headers, rows];
}

function lessonList(d: any): Table {
  const rows = (d.atamalar ?? []).filter((a: any) => a && typeof a === 'object').map((a: any) => [
    norm(a.class || a.sinif || a.class_name), norm(a.subject || a.ders), norm(a.teacher || a.ogretmen || a.teacher_name), norm(a.room || a.derslik), a.duration || a.saat || '', norm(a.type || a.dagilim),
  ]);
  return [['Sınıf', 'Ders', 'Öğretmen', 'Derslik', 'Haftalık Saat', 'Dağılım'], rows];
}

function entityList(d: any, kind: string): Table {
  const specs: Record<string, [string[], string[]]> = {
    ogretmenler: [['Ad', 'Kısa Ad', 'Branş', 'Günlük Max', 'Haftalık Max'], ['ad', 'kisa', 'brans', 'max_gunluk', 'max_haftalik']],
    siniflar: [['Ad', 'Kısa Ad', 'Mevcut', 'Sınıf Öğretmeni'], ['ad', 'kisa', 'mevcut', 'sinif_ogretmeni']],
    derslikler: [['Ad', 'Kısa Ad', 'Kapasite', 'Bina', 'Tür'], ['ad', 'kisa', 'kapasite', 'bina', 'tur']],
    dersler: [['Ad', 'Kısa Ad', 'Renk'], ['ad', 'kisa', 'renk']],
  };
  const [h, f] = specs[kind] ?? [['Ad'], ['ad']];
  return [h, (d[kind] ?? []).filter((x: any) => x && typeof x === 'object').map((x: any) => f.map((k) => norm(x[k] ?? '')))];
}

export const EXPORT_KINDS: [string, string][] = [
  ['timetable_classes', 'Ders Programı — Sınıflara Göre'],
  ['timetable_teachers', 'Ders Programı — Öğretmenlere Göre'],
  ['timetable_rooms', 'Ders Programı — Dersliklere Göre'],
  ['lessons', 'Ders Atama Listesi'],
  ['teachers', 'Öğretmen Listesi'],
  ['classes', 'Sınıf Listesi'],
  ['rooms', 'Derslik Listesi'],
  ['subjects', 'Ders Listesi'],
];

export function buildSheet(d: any, kind: string): [string, string[], (string | number)[][]] {
  switch (kind) {
    case 'timetable_classes': return ['Sınıf Programı', ...timetable(d, 'classes')];
    case 'timetable_teachers': return ['Öğretmen Programı', ...timetable(d, 'teachers')];
    case 'timetable_rooms': return ['Derslik Programı', ...timetable(d, 'rooms')];
    case 'lessons': return ['Ders Atamaları', ...lessonList(d)];
    case 'teachers': return ['Öğretmenler', ...entityList(d, 'ogretmenler')];
    case 'classes': return ['Sınıflar', ...entityList(d, 'siniflar')];
    case 'rooms': return ['Derslikler', ...entityList(d, 'derslikler')];
    case 'subjects': return ['Dersler', ...entityList(d, 'dersler')];
  }
  throw new Error(`bilinmeyen dışa aktarım türü: ${kind}`);
}

// ── CSV ──────────────────────────────────────────────────────────────────
export function toCsv(headers: string[], rows: (string | number)[][]): Blob {
  const q = (v: unknown) => {
    const s = v === null || v === undefined || v === '' ? '' : String(v).replace(/\n/g, ' / ');
    return /[";\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const text = [headers, ...rows].map((r) => r.map(q).join(';')).join('\r\n') + '\r\n';
  return new Blob(['﻿' + text], { type: 'text/csv;charset=utf-8' });
}

// ── XLSX ─────────────────────────────────────────────────────────────────
const CRC_TABLE = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
function crc32(b: Uint8Array): number { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = CRC_TABLE[(c ^ b[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }

/** Sıkıştırmasız (STORE) ZIP. */
function zip(files: [string, string][]): Blob {
  const enc = new TextEncoder();
  const parts: Uint8Array[] = [], central: Uint8Array[] = [];
  let offset = 0;
  for (const [name, content] of files) {
    const data = enc.encode(content), nm = enc.encode(name), crc = crc32(data);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true); lh.setUint16(8, 0, true);
    lh.setUint16(10, 0, true); lh.setUint16(12, 0x21, true); lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true);
    lh.setUint32(22, data.length, true); lh.setUint16(26, nm.length, true); lh.setUint16(28, 0, true);
    parts.push(new Uint8Array(lh.buffer), nm, data);
    const ch = new DataView(new ArrayBuffer(46));
    ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true); ch.setUint16(10, 0, true);
    ch.setUint16(12, 0, true); ch.setUint16(14, 0x21, true); ch.setUint32(16, crc, true); ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true);
    ch.setUint16(28, nm.length, true); ch.setUint16(30, 0, true); ch.setUint16(32, 0, true); ch.setUint16(34, 0, true); ch.setUint16(36, 0, true);
    ch.setUint32(38, 0, true); ch.setUint32(42, offset, true);
    central.push(new Uint8Array(ch.buffer), nm);
    offset += 30 + nm.length + data.length;
  }
  const cdSize = central.reduce((s, x) => s + x.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
  end.setUint32(12, cdSize, true); end.setUint32(16, offset, true);
  return new Blob([...parts, ...central, new Uint8Array(end.buffer)] as BlobPart[], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '');
function colName(i: number): string { let s = ''; i++; while (i > 0) { const m = (i - 1) % 26; s = String.fromCharCode(65 + m) + s; i = Math.floor((i - 1) / 26); } return s; }

export function toXlsx(sheets: [string, string[], (string | number)[][]][]): Blob {
  const files: [string, string][] = [];
  const names: string[] = [];
  sheets.forEach(([name, headers, rows], si) => {
    let safe = String(name).slice(0, 31);
    for (const ch of '[]:*?/\\') safe = safe.split(ch).join('-');
    safe = safe || 'Sayfa';
    while (names.includes(safe)) safe = `${safe.slice(0, 28)}_${si + 1}`;
    names.push(safe);
    const widths = headers.map((h) => String(h).length);
    for (const r of rows) r.forEach((v, i) => { if (i < widths.length) widths[i] = Math.max(widths[i], ...String(v ?? '').split('\n').map((p) => p.length)); });
    const cols = widths.map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${Math.min(Math.max(w + 2, 9), 34)}" customWidth="1"/>`).join('');
    const cell = (v: string | number, ref: string, style: number) => (typeof v === 'number'
      ? `<c r="${ref}" s="${style}"><v>${v}</v></c>`
      : v === '' || v === null || v === undefined ? `<c r="${ref}" s="${style}"/>` : `<c r="${ref}" s="${style}" t="inlineStr"><is><t xml:space="preserve">${esc(String(v))}</t></is></c>`);
    const xmlRows = [
      `<row r="1">${headers.map((h, i) => cell(String(h), `${colName(i)}1`, 1)).join('')}</row>`,
      ...rows.map((r, ri) => `<row r="${ri + 2}">${r.map((v, i) => cell(typeof v === 'number' ? v : String(v ?? ''), `${colName(i)}${ri + 2}`, i === 0 ? 2 : 3)).join('')}</row>`),
    ].join('');
    files.push([`xl/worksheets/sheet${si + 1}.xml`,
      `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>`
      + `<sheetViews><sheetView workbookViewId="0"><pane xSplit="1" ySplit="1" topLeftCell="B2" activePane="bottomRight" state="frozen"/></sheetView></sheetViews>`
      + `<cols>${cols}</cols><sheetData>${xmlRows}</sheetData><printOptions horizontalCentered="1"/>`
      + `<pageMargins left="0.4" right="0.4" top="0.5" bottom="0.5" header="0.3" footer="0.3"/><pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/></worksheet>`]);
  });
  files.unshift(
    ['[Content_Types].xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>${names.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join('')}</Types>`],
    ['_rels/.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`],
    ['xl/workbook.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>${names.map((n, i) => `<sheet name="${esc(n)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join('')}</sheets></workbook>`],
    ['xl/_rels/workbook.xml.rels', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${names.map((_, i) => `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join('')}<Relationship Id="rId${names.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`],
    ['xl/styles.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">`
      + `<fonts count="3"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><sz val="9"/><name val="Calibri"/></font></fonts>`
      + `<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E79"/><bgColor indexed="64"/></patternFill></fill></fills>`
      + `<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFB0B0B0"/></left><right style="thin"><color rgb="FFB0B0B0"/></right><top style="thin"><color rgb="FFB0B0B0"/></top><bottom style="thin"><color rgb="FFB0B0B0"/></bottom><diagonal/></border></borders>`
      + `<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>`
      + `<cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>`
      + `<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>`
      + `<xf numFmtId="0" fontId="2" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center" wrapText="1"/></xf>`
      + `<xf numFmtId="0" fontId="2" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf></cellXfs>`
      + `<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`],
  );
  return zip(files);
}

export function downloadBlob(blob: Blob, name: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 3000);
}

/** exporters.export_to_file — biçim uzantıdan; CSV tek bölüm tutar. */
export function exportFile(d: any, kinds: string[], xlsx: boolean): { blob: Blob; ext: string } {
  if (xlsx) return { blob: toXlsx(kinds.map((k) => buildSheet(d, k))), ext: '.xlsx' };
  const [, h, r] = buildSheet(d, kinds[0]);
  return { blob: toCsv(h, r), ext: '.csv' };
}
