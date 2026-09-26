// Çizelge üzerindeki işlemler — main_window._on_lesson_dropped, _delete_lesson_at,
// kilit ve sıfırlama. Masaüstündeki davranış korunur:
//   * kapalı saat / kural ihlali: gerekçe söylenir, karar kullanıcınındır;
//   * dolu hücre: tek ve aynı uzunlukta ders varsa TAKAS, yoksa yerinden olan
//     ders silinmez, yerleştirilemeyenlere döner;
//   * öğretmen çakışması uyarıdır, başka sınıfın dersi silinmez.
import { normKey } from '../engine/norm.ts';
import { matchesClass } from '../engine/norm.ts';
import { dayOf, dims, durOf, periodOf, subjectColor } from './model.ts';
import type { View } from './model.ts';
import {
  Candidate, FORBIDDEN, INVALID_GEOMETRY, Snapshot, analyze, classKey, hardViolations, lessonClasses, lessonTeachers,
  ruleViolations, teacherKey,
} from './placement.ts';
import { ask, getState, mutate, status } from './store.ts';

const uid = () => Math.random().toString(36).slice(2, 14);

export interface DropSource {
  lesson: any;                // ders bilgisi (subject, teacher, class/combined)
  duration: number;
  origin: { day: number; period: number } | null;   // ızgaradan taşınıyorsa
  blockId: string;            // ızgaradaki bloğun kimliği
  entries?: any[];            // ızgaradaki bloğun kayıtları
  looseId?: string;           // yerleştirilemeyenler panelindeki kart
}

function sameClass(a: string, b: string) {
  return a === b || matchesClass(a, b) || matchesClass(b, a) || classKey(a) === classKey(b);
}

/** Ders bırakma — masaüstündeki bütün sorular aynı sırayla. */
export async function dropLesson(src: DropSource, rowName: string, day: number, period: number) {
  const st = getState();
  const data = st.data;
  if (!data) return;
  const view: View = st.view;
  const { P, days } = dims(data);
  const dur = Math.max(1, src.duration);
  const dayName = days[day] ?? `${day + 1}. gün`;
  const lesson = { ...src.lesson, block_id: src.blockId, duration: dur,
    source: src.origin ? { day: src.origin.day, period: src.origin.period } : undefined };
  if (src.origin && src.origin.day === day && src.origin.period === period) return;

  if (period + dur > P) {
    await ask({ title: 'Geçersiz Konum', ok: 'Tamam', tone: 'warn',
      body: `Ders ${dur} saatlik olduğu için günün kalan saatlerine sığmıyor.\n\nGünün ${period + 1}. saatine bırakıldı, ancak gün ${P} saatten oluşuyor.` });
    return;
  }
  const snap = new Snapshot(data);
  const verdict = analyze(snap, { ...lesson, locked: false }, new Candidate(lesson, day, period, dur));
  const blocked: string[] = [];
  if (verdict.status === FORBIDDEN || verdict.status === INVALID_GEOMETRY) {
    for (const c of hardViolations(verdict).slice(0, 5)) blocked.push(c.message);
    if (!blocked.length && verdict.explanation) blocked.push(verdict.explanation);
  }
  const rules = ruleViolations(verdict);
  if (rules.length) {
    const lines = [...new Set(rules.map((c) => c.message))];
    const ok = await ask({ title: 'Planlama Kuralı', ok: 'Yine de yerleştir', cancel: 'Vazgeç', tone: 'warn',
      body: 'Planlama İlişkileri\'ndeki bir kural bu yerleşime izin vermiyor:\n\n' + lines.slice(0, 4).map((m) => '• ' + m).join('\n')
        + (lines.length > 4 ? '\n…' : '') + '\n\nYine de yerleştirirseniz ders çizelgede kalır; kural ihlali raporda görünmeye devam eder.' });
    if (!ok) { status('Yerleştirilemedi: ' + lines[0]); return; }
  }

  // Satır doğrulaması: ders yalnızca kendi sınıfının / öğretmeninin satırına.
  const subject = String(src.lesson.subject_name || src.lesson.subject || 'Ders');
  const teacher = lessonTeachers(src.lesson)[0] ?? '';
  const classes = lessonClasses(src.lesson);
  const isComb = classes.length > 1;
  if (view === 'teachers') {
    if (teacher && teacherKey(teacher) !== teacherKey(rowName)) {
      await ask({ title: 'Hatalı Öğretmen Satırı', ok: 'Tamam', tone: 'warn', body: `Bu ders ${teacher} öğretmenine aittir.\n\n${rowName} öğretmeninin satırına yerleştirilemez.` });
      return;
    }
  } else if (!classes.some((c) => sameClass(c, rowName))) {
    await ask({ title: 'Hatalı Sınıf Satırı', ok: 'Tamam', tone: 'warn',
      body: `Bu ders ${classes.join(' + ') || '?'} ${isComb ? 'sınıflarına' : 'sınıfına'} aittir.\n\n${rowName} sınıfının satırına yerleştirilemez.` });
    return;
  }

  const own = (p: any) => (src.blockId && String(p.block_id || '') === src.blockId) || (src.entries ?? []).includes(p);
  // 1) Sınıf hücreleri dolu mu? Her yerinden olan ders (yalnızca ilki değil).
  const occupied: any[] = [];
  for (const p of data.grid_placements ?? []) {
    if (own(p) || dayOf(p) !== day) continue;
    const overlap = Math.min(periodOf(p) + durOf(p), period + dur) - Math.max(periodOf(p), period);
    if (overlap <= 0) continue;
    const pc = String(p.class_name || p.class || '');
    if (classes.some((c) => sameClass(pc, c))) occupied.push(p);
  }
  const victims: any[] = [];
  const seenB = new Set<string>();
  for (const p of occupied) {
    const k = String(p.block_id || `${periodOf(p)}|${p.class_name || p.class}`);
    if (seenB.has(k)) continue;
    seenB.add(k);
    victims.push(p);
  }
  let swap: any = null;
  let displaced: any[] = [];
  if (victims.length) {
    const occ = victims[0];
    const occS = occ.subject_name || occ.subject || 'Ders', occT = occ.teacher_name || occ.teacher || 'Öğretmen';
    const occC = occ.class_name || occ.class || rowName;
    const blockLen = (v: any) => (data.grid_placements ?? []).filter((p: any) => v.block_id && p.block_id === v.block_id && String(p.class_name || p.class) === String(v.class_name || v.class)).reduce((s: number, p: any) => s + durOf(p), 0) || durOf(v);
    const occDur = blockLen(occ);
    if (victims.some((v) => v.locked || v.is_locked)) {
      await ask({ title: 'Kilitli Ders', ok: 'Tamam', tone: 'warn', body: `${occC} sınıfının ${dayName} günü ${period + 1}. saatindeki ${occS} dersi kilitli.\n\nKilitli ders yerinden oynatılamaz; önce kilidini açın.` });
      return;
    }
    const canSwap = !!src.origin && victims.length === 1 && occDur === dur;
    if (canSwap) {
      const ok = await ask({ title: 'Dersleri Yer Değiştir', ok: 'Yer değiştir', cancel: 'Vazgeç',
        body: `${occC} sınıfının ${dayName} günü ${period + 1}. saatinde ${occS} (${occT}) dersi var.\n\nİki dersin yerini değiştirmek istiyor musunuz?\nHiçbir ders silinmez — sadece yerleri takas edilir.` });
      if (!ok) { status('Yer değiştirme iptal edildi.'); return; }
      swap = occ;
    } else {
      const names = victims.slice(0, 4).map((o) => `${o.subject_name || o.subject || 'Ders'} (${blockLen(o)} saat)`).join(', ') + (victims.length > 4 ? ` ve ${victims.length - 4} ders daha` : '');
      const why = victims.length === 1 && occDur !== dur
        ? `${dur} saatlik ders ile ${occDur} saatlik ders yer değiştiremez: takas edilseydi uzun olan, yanındaki başka bir dersin üstüne taşardı.`
        : victims.length > 1 ? `Bu aralıkta ${victims.length} ders var; takasın tek bir karşılığı yok.` : 'Bu ders ızgaradan sürüklenmediği için takas edilemiyor.';
      const ok = await ask({ title: 'Takas Edilemiyor — Ders Aşağı Alınacak', ok: 'Devam', cancel: 'Vazgeç', tone: 'warn',
        body: `${occC} sınıfının ${dayName} günü ${period + 1}. saatinde ${names} var.\n\n${why}\n\nDevam ederseniz ${names} "Yerleştirilemeyenler" alanına alınır — silinmez, oradan istediğiniz saate sürükleyebilirsiniz.` });
      if (!ok) { status(`İptal edildi: ${rowName} — ${dayName} ${period + 1}. saat dolu.`); return; }
      displaced = victims;
    }
  }
  // 2) Kapalı saat — tek soru.
  if (blocked.length) {
    const uniq = [...new Set(blocked)];
    const ok = await ask({ title: 'Kapalı Saat', ok: 'Yine de yerleştir', cancel: 'Vazgeç', tone: 'warn',
      body: uniq.slice(0, 6).join('\n') + (uniq.length > 6 ? '\n…' : '') + '\n\nBu saat kapalı işaretli. Yine de yerleştirirseniz ders çizelgede kalır; kapalı saat uyarısı görünmeye devam eder.' });
    if (!ok) { status('Yerleştirilemedi: ' + uniq[0]); return; }
  }
  // 3) Öğretmen çakışması: uyarı, silme yok.
  let teacherConflict = false;
  if (teacher) {
    const clash = (data.grid_placements ?? []).find((p: any) => {
      if (own(p) || dayOf(p) !== day) return false;
      if (!lessonTeachers(p).some((t) => teacherKey(t) === teacherKey(teacher))) return false;
      const overlap = Math.min(periodOf(p) + durOf(p), period + dur) - Math.max(periodOf(p), period);
      if (overlap <= 0) return false;
      const pc = String(p.class_name || p.class || '');
      const sameJoint = isComb && (normKey(p.subject_name || p.subject) === normKey(subject) || p.is_combined);
      return !sameJoint && !classes.some((c) => sameClass(pc, c)) && !victims.includes(p);
    });
    if (clash) {
      const ok = await ask({ title: 'Öğretmen Çakışması', ok: 'Yine de yerleştir', cancel: 'Vazgeç', tone: 'warn',
        body: `${teacher} öğretmeni ${dayName} günü ${period + 1}. saatte zaten ${clash.class_name || clash.class} sınıfında ${clash.subject_name || clash.subject} dersinde görünüyor.\n\nYine de yerleştirilsin mi? Hiçbir ders silinmez; çakışma kalır.` });
      if (!ok) { status(`İptal edildi: ${teacher} — ${dayName} ${period + 1}. saat.`); return; }
      teacherConflict = true;
    }
  }
  // 4) Uygula — tek geri alınabilir adım.
  mutate(src.origin ? 'Ders taşındı' : 'Ders yerleştirildi', (d) => {
    const g: any[] = d.grid_placements ?? (d.grid_placements = []);
    const ownIdx = new Set<number>();
    const current: any[] = getState().data.grid_placements ?? [];
    current.forEach((p, i) => { if (own(p)) ownIdx.add(i); });
    const victimIdx = new Set<number>();
    const vs = swap ? [swap] : displaced;
    current.forEach((p, i) => {
      if (vs.some((v) => (v.block_id && p.block_id === v.block_id) || (dayOf(p) === dayOf(v) && periodOf(p) === periodOf(v) && String(p.class_name || p.class) === String(v.class_name || v.class)))) victimIdx.add(i);
    });
    const victimEntries = g.filter((_, i) => victimIdx.has(i));
    d.grid_placements = g.filter((_, i) => !ownIdx.has(i) && !victimIdx.has(i));
    // Yerinden olanın atamalarda karşılığı yoksa (dolgu vb.) kaybolmasın: panele kart.
    if (displaced.length) {
      for (const v of displaced) {
        const hasAssign = (d.atamalar ?? []).some((a: any) => normKey(a.subject || a.ders) === normKey(v.subject_name || v.subject));
        if (!hasAssign) {
          (d.loose_unplaced_cards ??= []).push({ id: `loose_${uid()}`, subject_name: v.subject_name || v.subject, subject: v.subject_name || v.subject,
            teacher_name: v.teacher_name || v.teacher, teacher: v.teacher_name || v.teacher, class_name: v.class_name || v.class,
            class: v.class_name || v.class, duration: victimEntries.filter((x) => x.block_id === v.block_id).reduce((s, x) => s + durOf(x), 0) || durOf(v),
            color: v.color || '', is_combined: !!v.is_combined, combined_classes: v.combined_classes || [] });
        }
      }
    }
    const blockId = uid();
    const color = subjectColor(subject, d);
    const targets = isComb ? classes : [view === 'classes' ? rowName : (classes[0] ?? rowName)];
    for (let k = 0; k < dur; k++) {
      for (const cls of targets) {
        d.grid_placements.push({ day, period: period + k, row: period + k, col: day, class_name: cls, class: cls,
          teacher_name: teacher, teacher, subject_name: subject, subject, duration: 1, locked: false, is_manual: true,
          color, is_combined: isComb, combined_classes: isComb ? [...classes] : [], block_id: blockId, is_filler: false,
          has_conflict: teacherConflict });
      }
    }
    if (swap && src.origin) {
      const sb = uid();
      const sClasses = swap.is_combined && (swap.combined_classes ?? []).length ? swap.combined_classes : [swap.class_name || swap.class];
      const sDur = victimEntries.filter((x) => String(x.class_name || x.class) === String(swap.class_name || swap.class)).reduce((s, x) => s + durOf(x), 0) || durOf(swap);
      for (let k = 0; k < sDur; k++) {
        for (const cls of sClasses) {
          d.grid_placements.push({ day: src.origin.day, period: src.origin.period + k, row: src.origin.period + k, col: src.origin.day,
            class_name: cls, class: cls, teacher_name: swap.teacher_name || swap.teacher || '', teacher: swap.teacher_name || swap.teacher || '',
            subject_name: swap.subject_name || swap.subject || '', subject: swap.subject_name || swap.subject || '', duration: 1,
            locked: !!swap.locked, is_manual: true, color: swap.color || '', is_combined: !!swap.is_combined,
            combined_classes: [...(swap.combined_classes ?? [])], block_id: sb, is_filler: !!swap.is_filler });
        }
      }
    }
    if (src.looseId) d.loose_unplaced_cards = (d.loose_unplaced_cards ?? []).filter((c: any) => String(c.id) !== src.looseId);
    if ('auto_schedule_results' in d) d.auto_schedule_results = [...d.grid_placements];
  });
  status(blocked.length ? 'Kapalı saate elle yerleştirildi.' : teacherConflict ? `Çakışmayla yerleştirildi: ${teacher}` : `${subject} → ${dayName} ${period + 1}. saat`);
}

/** Bloğu çizelgeden kaldırır; ders yerleştirilemeyenlere döner (silinmez). */
export async function removeBlock(entries: any[]) {
  const st = getState();
  if (!st.data || !entries.length) return;
  const e0 = entries[0];
  if (entries.some((e) => e.locked || e.is_locked)) {
    const ok = await ask({ title: 'Kilitli Ders', ok: 'Kilidi aç ve kaldır', cancel: 'Vazgeç', tone: 'warn',
      body: `${e0.subject_name || e0.subject} dersi kilitli.\n\nKaldırırsanız kilit de kalkar; ders yerleştirilemeyenlere döner.` });
    if (!ok) return;
  }
  const bid = String(e0.block_id || '');
  mutate('Ders kaldırıldı', (d) => {
    const cur: any[] = getState().data.grid_placements ?? [];
    const drop = new Set<number>();
    cur.forEach((p, i) => { if ((bid && String(p.block_id || '') === bid) || entries.includes(p)) drop.add(i); });
    d.grid_placements = (d.grid_placements ?? []).filter((_: any, i: number) => !drop.has(i));
    if ('auto_schedule_results' in d) d.auto_schedule_results = [...d.grid_placements];
  });
  status(`${e0.subject_name || e0.subject} kaldırıldı — yerleştirilemeyenlere döndü.`);
}

export function toggleLock(entries: any[]) {
  const st = getState();
  if (!st.data || !entries.length) return;
  const lock = !entries.every((e) => e.locked || e.is_locked);
  const bid = String(entries[0].block_id || '');
  mutate(lock ? 'Ders kilitlendi' : 'Kilit açıldı', (d) => {
    const cur: any[] = getState().data.grid_placements ?? [];
    cur.forEach((p, i) => {
      if ((bid && String(p.block_id || '') === bid) || entries.includes(p)) {
        d.grid_placements[i].locked = lock;
        if (!lock) delete d.grid_placements[i].is_locked;
      }
    });
  });
  status(lock ? 'Ders kilitlendi — planlayıcı yerinde bırakır.' : 'Kilit açıldı.');
}

export function lockRow(rowName: string, view: View, lock: boolean) {
  mutate(lock ? 'Satır kilitlendi' : 'Satır kilidi açıldı', (d) => {
    for (const p of d.grid_placements ?? []) {
      const owners = view === 'classes' ? [p.class_name || p.class] : lessonTeachers(p);
      const hit = view === 'classes' ? owners.some((o: string) => sameClass(String(o), rowName)) : owners.some((o: string) => teacherKey(o) === teacherKey(rowName));
      if (hit) { p.locked = lock; if (!lock) delete p.is_locked; }
    }
  });
}

/** main_window._act_clear_schedule */
export function resetSchedule(keepLocked: boolean) {
  mutate(keepLocked ? 'Çizelge sıfırlandı (kilitliler kaldı)' : 'Çizelge sıfırlandı', (d) => {
    const locked = (d.grid_placements ?? []).filter((p: any) => p && (p.locked || p.is_locked));
    if (keepLocked) {
      const keep = new Set(locked.map((p: any) => String(p.block_id || '')).filter(Boolean));
      d.grid_placements = locked;
      d.auto_schedule_results = (d.auto_schedule_results ?? []).filter((p: any) => keep.has(String(p?.block_id || '')));
    } else {
      d.grid_placements = [];
      d.auto_schedule_results = [];
    }
    d.yerlesim = {};
    d.loose_unplaced_cards = [];
    d.manual_unplaced_cards = [];
  });
}

/** Oto planlayıcının sonucu çizelgeye. */
export function applyPlan(result: any) {
  mutate('Otomatik planlama', (d) => {
    d.grid_placements = result.schedule;
    d.auto_schedule_results = [...result.schedule];
    d.yerlesim = {};
    d.loose_unplaced_cards = [];
    d.manual_unplaced_cards = [];
  });
  status(`Otomatik planlama uygulandı: ${result.placed_hours}/${result.total_assigned_hours} saat.`);
}
