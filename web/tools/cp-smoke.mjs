import CpSat from 'or-tools-wasm/cp-sat';
// küçük bir model: 40 bool, en fazla 20 seçilsin, en büyükle
const n = 400;
const vars = [], cons = [];
for (let i = 0; i < n; i++) vars.push({ domain: [0, 1] });
cons.push({ linear: { vars: [...Array(n).keys()], coeffs: Array(n).fill(1), domain: [0, 200] } });
// zor yapsın diye çiftler
for (let i = 0; i + 1 < n; i += 2) cons.push({ boolOr: { literals: [-(i) - 1, -(i + 1) - 1] } });
const proto = { variables: vars, constraints: cons, objective: { vars: [...Array(n).keys()], coeffs: Array(n).fill(-1), offset: 0, scalingFactor: -1 } };
let t = performance.now();
const bytes = await CpSat.createModel(proto);
console.log('createModel ms', (performance.now() - t).toFixed(1), 'bytes', bytes.length);
t = performance.now();
const r = await CpSat.solve(bytes, { maxTimeInSeconds: 5, numWorkers: 8, randomSeed: 3, stopAfterFirstSolution: false });
console.log('solve ms', (performance.now() - t).toFixed(1), r.response.status, r.response.objectiveValue, r.response.bestObjectiveBound, 'sol len', r.response.solution.length);
// iptal testi: çözümsüz ve zor bir model — 30 sn süre, 1 sn sonra iptal
const m = 60, v2 = [], c2 = [];
for (let i = 0; i < m * m; i++) v2.push({ domain: [0, 1] });
for (let i = 0; i < m; i++) { c2.push({ linear: { vars: [...Array(m).keys()].map(j => i * m + j), coeffs: Array(m).fill(1), domain: [1, 1] } }); c2.push({ linear: { vars: [...Array(m).keys()].map(j => j * m + i), coeffs: Array(m).fill(1), domain: [1, 1] } }); }
const obj = { vars: [...Array(m * m).keys()], coeffs: [...Array(m * m).keys()].map(k => (k * 7919) % 101), offset: 0, scalingFactor: 1 };
const b2 = await CpSat.createModel({ variables: v2, constraints: c2, objective: obj });
t = performance.now();
setTimeout(() => { console.log('cancel @', (performance.now() - t).toFixed(0)); CpSat.cancelSolve(); }, 1500);
const r2 = await CpSat.solve(b2, { maxTimeInSeconds: 30, numWorkers: 8 });
console.log('after cancel ms', (performance.now() - t).toFixed(0), r2.response.status, r2.response.objectiveValue, r2.response.bestObjectiveBound);
process.exit(0);
