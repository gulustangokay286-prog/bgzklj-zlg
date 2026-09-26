// CpModelProto için küçük, hızlı protobuf kodlayıcı.
//
// or-tools-wasm modeli protobufjs ile doğrulayıp kodluyor; Boğaziçi'nde tek
// bir model çağrı başına ~0,9 sn tutuyordu ve optimal kip onlarca çağrı
// yapıyor. Taban model (bütün kural kısıtları) bir kez kodlanır; her çağrıda
// yalnızca eklenenler (amaç, sabitlemeler, ipuçları) kodlanıp arkasına
// eklenir. Protobuf'ta tekrarlı alanlar birleştirmede sırayla eklendiği için
// taban + ek bayt dizisi, birleşik modelin birebir kodudur.

export class Writer {
  buf = new Uint8Array(1 << 16);
  len = 0;

  private ensure(n: number) {
    if (this.len + n <= this.buf.length) return;
    let cap = this.buf.length * 2;
    while (cap < this.len + n) cap *= 2;
    const nb = new Uint8Array(cap);
    nb.set(this.buf.subarray(0, this.len));
    this.buf = nb;
  }

  byte(b: number) {
    this.ensure(1);
    this.buf[this.len++] = b;
  }

  varint(n: number) {
    // negatif olmayan, 2^53'e kadar
    this.ensure(10);
    while (n > 127) {
      this.buf[this.len++] = (n % 128) | 128;
      n = Math.floor(n / 128);
    }
    this.buf[this.len++] = n;
  }

  /** int32/int64 alanı (negatifse 64 bit ikiye tümleyen, 10 bayt). */
  int(n: number) {
    if (n >= 0) { this.varint(n); return; }
    const m = -n;
    let lo = m % 4294967296, hi = Math.floor(m / 4294967296);
    lo = (~lo) >>> 0;
    hi = (~hi) >>> 0;
    lo = (lo + 1) >>> 0;
    if (lo === 0) hi = (hi + 1) >>> 0;
    this.ensure(10);
    while (hi > 0 || lo > 127) {
      this.buf[this.len++] = (lo & 0x7f) | 0x80;
      lo = ((lo >>> 7) | (hi << 25)) >>> 0;
      hi >>>= 7;
    }
    this.buf[this.len++] = lo;
  }

  tag(field: number, wire: number) {
    this.varint(field * 8 + wire);
  }

  double(field: number, v: number) {
    this.tag(field, 1);
    this.ensure(8);
    new DataView(this.buf.buffer, this.buf.byteOffset + this.len, 8).setFloat64(0, v, true);
    this.len += 8;
  }

  bytes(b: Uint8Array) {
    this.ensure(b.length);
    this.buf.set(b, this.len);
    this.len += b.length;
  }

  /** Uzunluk önekli alt ileti: içerik geçici yazıcıda kurulur. */
  message(field: number, body: (w: Writer) => void) {
    const sub = scratch();
    body(sub);
    this.tag(field, 2);
    this.varint(sub.len);
    this.bytes(sub.buf.subarray(0, sub.len));
    release(sub);
  }

  packed(field: number, xs: ArrayLike<number>) {
    if (!xs.length) return;
    const sub = scratch();
    for (let i = 0; i < xs.length; i++) sub.int(xs[i]);
    this.tag(field, 2);
    this.varint(sub.len);
    this.bytes(sub.buf.subarray(0, sub.len));
    release(sub);
  }

  result(): Uint8Array {
    return this.buf.slice(0, this.len);
  }
}

const pool: Writer[] = [];
function scratch(): Writer {
  const w = pool.pop() ?? new Writer();
  w.len = 0;
  return w;
}
function release(w: Writer) {
  if (pool.length < 16) pool.push(w);
}

function linearExpr(w: Writer, e: { vars: number[]; coeffs: number[]; offset?: number }) {
  w.packed(1, e.vars);
  w.packed(2, e.coeffs);
  if (e.offset) { w.tag(3, 0); w.int(e.offset); }
}

export function encodeVars(w: Writer, domains: number[][], from = 0) {
  for (let i = from; i < domains.length; i++) {
    const d = domains[i];
    w.message(2, (x) => x.packed(2, d));
  }
}

export function encodeConstraint(w: Writer, c: any) {
  w.message(3, (x) => {
    if (c.enforcementLiteral) x.packed(2, c.enforcementLiteral);
    if (c.linear) x.message(12, (y) => { y.packed(1, c.linear.vars); y.packed(2, c.linear.coeffs); y.packed(3, c.linear.domain); });
    else if (c.boolOr) x.message(3, (y) => y.packed(1, c.boolOr.literals));
    else if (c.atMostOne) x.message(26, (y) => y.packed(1, c.atMostOne.literals));
    else if (c.linMax) x.message(27, (y) => {
      y.message(1, (z) => linearExpr(z, c.linMax.target));
      for (const e of c.linMax.exprs) y.message(2, (z) => linearExpr(z, e));
    });
    else throw new Error('Kodlanamayan kısıt: ' + Object.keys(c).join(','));
  });
}

export function encodeCons(w: Writer, cons: any[], from = 0) {
  for (let i = from; i < cons.length; i++) encodeConstraint(w, cons[i]);
}

export function encodeObjective(w: Writer, o: { vars: number[]; coeffs: number[]; offset: number; scalingFactor: number }) {
  w.message(4, (x) => {
    x.packed(1, o.vars);
    if (o.offset) x.double(2, o.offset);
    x.double(3, o.scalingFactor);
    x.packed(4, o.coeffs);
  });
}

export function encodeHint(w: Writer, vars: number[], values: number[]) {
  if (!vars.length) return;
  w.message(6, (x) => { x.packed(1, vars); x.packed(2, values); });
}
