// version_store.py karşılığı (tarayıcıda, IndexedDB): kurumlar ve her kurumun
// kayıtlı sürümleri. "Kaydet" yeni sürüm yazar ve onu yayındaki sürüm yapar.
import * as db from './db.ts';
import { hourTotals } from './model.ts';
import { getState, load, setState, status, tell } from './store.ts';

export interface Institution { slug: string; name: string; color: string; created: number; updated: number; active: string | null }
export interface VersionInfo {
  id: string; n: number; created: number; source: 'manual' | 'import' | 'plan' | 'new';
  name?: string; note?: string;
  summary: { classes: number; teachers: number; subjects: number; assigned: number; placed: number };
}

export const INST_COLORS = ['#0071E3', '#34C759', '#FF9500', '#AF52DE', '#FF2D55', '#5AC8FA', '#FFCC00', '#8E8E93', '#A30F37', '#1E3A8A'];

const TR: Record<string, string> = { 'ı': 'i', 'İ': 'i', 'ş': 's', 'Ş': 's', 'ğ': 'g', 'Ğ': 'g', 'ü': 'u', 'Ü': 'u', 'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c' };
/** version_store.slugify */
export function slugify(name: string): string {
  const s = [...String(name)].map((c) => TR[c] ?? c).join('').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return s || 'kurum';
}

export async function listInstitutions(): Promise<Institution[]> {
  return (await db.get<Institution[]>('institutions')) ?? [];
}
async function putInstitutions(list: Institution[]) { await db.set('institutions', list); }

export async function createInstitution(name: string, color = INST_COLORS[0]): Promise<Institution> {
  const list = await listInstitutions();
  let slug = slugify(name), i = 2;
  while (list.some((x) => x.slug === slug)) slug = `${slugify(name)}_${i++}`;
  const inst: Institution = { slug, name: name.trim(), color, created: Date.now(), updated: Date.now(), active: null };
  await putInstitutions([...list, inst]);
  return inst;
}

export async function updateInstitution(slug: string, patch: Partial<Institution>) {
  const list = await listInstitutions();
  await putInstitutions(list.map((x) => (x.slug === slug ? { ...x, ...patch, updated: Date.now() } : x)));
  const cur = getState().inst;
  if (cur?.slug === slug) setState({ inst: { ...cur, name: patch.name ?? cur.name, color: patch.color ?? cur.color } });
}

export async function deleteInstitution(slug: string) {
  for (const v of await listVersions(slug)) await db.del(`version:${slug}:${v.id}`);
  await db.del(`versions:${slug}`);
  await putInstitutions((await listInstitutions()).filter((x) => x.slug !== slug));
}

export async function listVersions(slug: string): Promise<VersionInfo[]> {
  return (await db.get<VersionInfo[]>(`versions:${slug}`)) ?? [];
}

function summaryOf(d: any): VersionInfo['summary'] {
  const { assigned, placed } = hourTotals(d);
  return { classes: (d.siniflar ?? []).length, teachers: (d.ogretmenler ?? []).length, subjects: (d.dersler ?? []).length, assigned, placed };
}

/** version_store.save_version + set_active_version */
export async function addVersion(slug: string, data: any, source: VersionInfo['source'], note = ''): Promise<VersionInfo> {
  const list = await listVersions(slug);
  const n = list.reduce((m, v) => Math.max(m, v.n), 0) + 1;
  const info: VersionInfo = { id: `v${n}_${Date.now().toString(36)}`, n, created: Date.now(), source, note: note || undefined, summary: summaryOf(data) };
  await db.set(`version:${slug}:${info.id}`, data);
  await db.set(`versions:${slug}`, [...list, info]);
  await updateInstitution(slug, { active: info.id });
  return info;
}

export async function loadVersionData(slug: string, id: string): Promise<any> {
  return db.get<any>(`version:${slug}:${id}`);
}

export async function deleteVersion(slug: string, id: string) {
  await db.del(`version:${slug}:${id}`);
  const rest = (await listVersions(slug)).filter((v) => v.id !== id);
  await db.set(`versions:${slug}`, rest);
  const inst = (await listInstitutions()).find((x) => x.slug === slug);
  if (inst?.active === id) await updateInstitution(slug, { active: rest.length ? rest[rest.length - 1].id : null });
}

export async function patchVersion(slug: string, id: string, patch: Partial<Pick<VersionInfo, 'name' | 'note'>>) {
  const list = await listVersions(slug);
  await db.set(`versions:${slug}`, list.map((v) => (v.id === id ? { ...v, ...patch } : v)));
}

export function versionLabel(v: VersionInfo): string {
  return v.name?.trim() || `Sürüm ${v.n}`;
}

/** Sürümü açar (Anasayfa → Aç). */
export async function openVersion(inst: Institution, v: VersionInfo) {
  const data = await loadVersionData(inst.slug, v.id);
  if (!data) { await tell('Açılamadı', 'Bu sürümün verisi bulunamadı.'); return; }
  load(data, `${inst.name} — ${versionLabel(v)}`, { inst: { slug: inst.slug, name: inst.name, color: inst.color }, versionId: v.id });
  await updateInstitution(inst.slug, { active: v.id });
}

/** Kaydet: açık çizelgeyi yeni sürüm olarak yazar (main_window._act_save). */
export async function saveVersion(note = ''): Promise<void> {
  const s = getState();
  if (!s.data) return;
  let inst = s.inst;
  if (!inst) {
    const base = (s.name || 'Kurum').replace(/\s+—\s+.*$/, '').trim() || 'Kurum';
    const created = await createInstitution(base);
    inst = { slug: created.slug, name: created.name, color: created.color };
  }
  const v = await addVersion(inst.slug, structuredClone(s.data), 'manual', note);
  setState({ inst, versionId: v.id, dirty: false, name: `${inst.name} — ${versionLabel(v)}` });
  status(`'${inst.name}' için ${versionLabel(v)} kaydedildi ve yayına alındı.`);
}
