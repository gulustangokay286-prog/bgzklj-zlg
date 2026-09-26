// dialogs/preflight_dialog.run_preflight: sorun yoksa hiçbir şey göstermez,
// varsa sayılarla anlatır; kullanıcı yine de devam edebilir.
import { checkFeasibility, formatReport } from './feasibility.ts';
import { ask } from './store.ts';

export async function runPreflight(probe: any, mode: 'save' | 'plan' = 'save', note = ''): Promise<boolean> {
  let r;
  try { r = checkFeasibility(probe); } catch (e) { console.warn('[preflight] kontrol çalışmadı', e); return true; }
  if (r.ok) return true;
  const plan = mode === 'plan';
  return ask({
    title: plan ? 'Bu ayarlarla çizelgenin tamamı dolmaz' : 'Planlayıcı bu ayarla çizelgeyi dolduramaz',
    body: 'Aşağıdakiler bir tercih meselesi değil, aritmetik: bir öğretmen aynı anda tek sınıfta olabilir.',
    lines: formatReport(r, probe),
    note,
    foot: "Devam ederseniz yerleşemeyen dersler alttaki 'Yerleştirilmeyenler' listesine düşer; hiçbiri silinmez.",
    ok: plan ? 'Yoksay ve Devam Et' : 'Yine de Kaydet',
    cancel: plan ? 'Vazgeç' : 'Geri Dön ve Düzelt',
    tone: 'danger',
  });
}
