// Rapor sayfalarının biçimi. Hem ekrandaki önizlemede hem yazdırırken hem de
// "HTML Çıktısı" dosyasında aynı kurallar kullanılır.
export const PRINT_CSS = `
.pp-page { background: #fff; color: #000; box-sizing: border-box; overflow: hidden; position: relative; font-family: "Segoe UI", Arial, sans-serif; }
.pp-page.land { width: 297mm; height: 210mm; padding: 6mm 7mm; }
.pp-page.port { width: 210mm; min-height: 297mm; padding: 7mm 6mm; }
.pp-page.port.flow { height: auto; }
.pp-page * { box-sizing: border-box; }
.pp-foot { display: flex; justify-content: space-between; font-size: 10px; color: #475569; margin-top: 6px; }
.pp-page.land .pp-foot { position: absolute; left: 7mm; right: 7mm; bottom: 4mm; }

/* 6'lı / tekil çizelge */
.pp-page.six { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: repeat(3, 1fr); gap: 7mm 8mm; }
.mg { display: flex; flex-direction: column; min-height: 0; height: 100%; }
.mg-head { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; font-size: 8px; margin-bottom: 2px; }
.mg-head b { font-size: 16px; letter-spacing: .02em; }
.mg-head span:last-child { text-align: right; }
.mg.single .mg-head { font-size: 14px; margin-bottom: 6px; }
.mg.single .mg-head b { font-size: 32px; }
.mg-grid { width: 100%; flex: 1; border-collapse: collapse; table-layout: fixed; }
.mg-grid th, .mg-grid td { border: 1px solid #000; text-align: center; vertical-align: middle; padding: 0 1px; overflow: hidden; }
.mg-grid thead th { font-weight: 700; height: 1.2em; }
.mg-grid thead th b { display: block; font-size: 11.5px; line-height: 1.1; }
.mg-grid thead th small { display: block; font-size: 8px; font-weight: 700; line-height: 1.1; }
.mg.single .mg-grid thead th b { font-size: 18px; }
.mg.single .mg-grid thead th small { font-size: 13px; }
.mg-grid tbody th { width: 9%; font-size: 12px; font-weight: 700; }
.mg.single .mg-grid tbody th { font-size: 24px; }
.mg-grid thead th:first-child { width: 9%; }
.mg-cell { position: relative; }
.mg-cell b { display: block; font-size: 10px; line-height: 1.1; }
.mg-cell b.sm { font-size: 8px; }
.mg-cell span { display: block; font-size: 7px; line-height: 1.1; color: #111; }
.mg-cell span.sm { font-size: 6px; }
.mg.single .mg-cell b { font-size: 20px; } .mg.single .mg-cell b.sm { font-size: 15px; }
.mg.single .mg-cell span { font-size: 15px; } .mg.single .mg-cell span.sm { font-size: 12px; }
.mg-link { position: absolute; top: 1px; right: 2px; font-style: normal; font-size: 8px; background: #dbeafe; border: 1px solid #2563eb; border-radius: 2px; line-height: 1; padding: 1px; }
.mg-closed { background: #f1f5f9; }
.mg-closed.x::after, .cs-closed.x::after { content: "✕"; color: #a0aec0; font-size: 8px; }
@media print { .mg-closed, .cs-closed { background: #e3e6eb !important; } }

/* çarşaf */
.cs-head { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px; }
.cs-grid { width: 100%; border-collapse: collapse; table-layout: fixed; }
.cs-grid th, .cs-grid td { border: 1px solid #94a3b8; text-align: center; font-size: 8px; height: 16.5px; padding: 0; overflow: hidden; white-space: nowrap; }
.cs-grid thead th { background: #f1f5f9; font-weight: 700; }
.cs-grid thead tr:first-child th { font-size: 10px; }
.cs-grid thead tr:first-child th:first-child { width: 80px; font-size: 10px; }
.cs-grid tbody th { font-size: 10px; font-weight: 700; text-align: center; background: #f8fafc; }
.cs-grid .ds { border-left: 2px solid #000; }
.cs-l { font-weight: 700; font-size: 8.5px !important; }
.cs-closed { background: #f1f5f9; }
.cs-legend { margin-top: 8px; border: 1px solid #cbd5e1; border-radius: 5px; padding: 5px 10px; font-size: 9px; }
.cs-leg-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px 10px; margin-top: 3px; }
.cs-leg-grid div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 8.5px; }

/* ders tablosu */
.lt-title { text-align: center; font-size: 34px; font-weight: 800; margin-top: 8mm; }
.lt-school { font-size: 12px; margin: 2mm 0 3mm; }
.lt-grid { width: 100%; border-collapse: collapse; table-layout: fixed; }
.lt-grid th, .lt-grid td { border: 1px solid #000; text-align: center; height: 20mm; font-size: 11px; }
.lt-grid thead th { height: 14mm; }
.lt-grid thead th b { display: block; font-size: 16px; }
.lt-grid thead th small { display: block; font-size: 10px; }
.lt-grid tbody th { width: 70px; font-size: 16px; }
.lt-grid td b { display: block; font-size: 12px; }
.lt-grid td span { display: block; font-size: 9px; }

/* liste raporları */
.cl-top { display: flex; justify-content: space-between; font-size: 13px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }
.cl-top span { color: #64748b; font-size: 11px; font-weight: 700; }
.cl-ent { display: flex; gap: 10px; align-items: center; margin: 10px 0; }
.cl-ent b { display: block; font-size: 17px; }
.cl-ent small { color: #475569; font-size: 11px; font-weight: 700; }
.cl-avatar { width: 30px; height: 30px; border-radius: 50%; background: #94a3b8; }
.cl-banner { display: flex; justify-content: space-between; align-items: center; border: 1px solid #cbd5e1; border-radius: 4px; padding: 7px 12px; font-size: 12px; margin-bottom: 8px; }
.cl-banner span { font-size: 10px; color: #475569; font-weight: 700; }
.cl-block { break-inside: avoid; margin-bottom: 8px; }
.cl-bh { display: flex; gap: 14px; align-items: center; background: #f1f5f9; border-radius: 3px; padding: 5px 10px; font-size: 10.5px; }
.cl-bh .sp { flex: 1; }
.cl-table { width: 100%; border-collapse: collapse; font-size: 9.5px; }
.cl-table th { background: #0f172a; color: #fff; text-align: left; padding: 4px 6px; font-size: 9px; }
.cl-table td { border-bottom: 1px solid #e2e8f0; padding: 3px 6px; }
.cl-table tr:nth-child(even) td { background: #f8fafc; }
.cl-table td.c, .cl-table th:nth-child(n+3) { text-align: center; }
.cl-badge { display: inline-block; min-width: 44px; margin-right: 6px; padding: 2px 4px; border-radius: 3px; font-weight: 800; text-align: center; font-size: 8.5px; color: #0f172a; }

/* ders yükü */
.tl-banner { display: flex; justify-content: space-between; align-items: center; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px; }
.tl-banner b { font-size: 17px; }
.tl-banner span { font-size: 11px; color: #475569; font-weight: 700; }
.tl-table { width: 100%; border-collapse: collapse; font-size: 10.5px; table-layout: fixed; }
.tl-table th { background: #0f172a; color: #fff; padding: 6px 8px; text-align: left; }
.tl-table th:nth-child(1) { width: 26%; } .tl-table th:nth-child(2) { width: 13%; } .tl-table th:nth-child(4) { width: 14%; }
.tl-table td { padding: 3px 8px; border-bottom: 1px solid #e2e8f0; }
.tl-table tr:nth-child(even) td { background: #f8fafc; }
.tl-table td.el { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tl-table td.c { text-align: center; font-weight: 700; }
`;

export const PRINT_ROOT_CSS = `
#print-root { display: none; }
@media print {
  html, body { background: #fff !important; }
  body > #root { display: none !important; }
  #print-root { display: block; }
  #print-root .pp-page { page-break-after: always; break-after: page; box-shadow: none !important; margin: 0 !important; }
  #print-root .pp-page:last-child { page-break-after: auto; break-after: auto; }
}
`;
