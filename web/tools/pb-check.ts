// Kendi kodlayıcımız ile or-tools-wasm'ın protobufjs kodlaması aynı modeli mi üretiyor?
import CpSat from 'or-tools-wasm/cp-sat';
import protobuf from 'protobufjs';
import { Expr, Model, NOT } from '../src/engine/cp.ts';

const m = new Model();
const a = m.bool(), b = m.bool(), c = m.int(-5, 9007199254740991), d = m.bool();
m.le(Expr.of([a, b]).add(c, -3), 7, [NOT(d)]);
m.ge(Expr.of([a]).add(NOT(b), 2).constant(4), -9007199254740991);
m.boolOr([NOT(a), b]);
m.atMostOne([a, NOT(b), d]);
m.implication(a, NOT(d));
m.maxEquality(d, [a, NOT(b)]);
const f = m.fork();
const e = f.bool();
f.eq(Expr.of([e, a]), 1, [b]);
f.maximize(Expr.of([a, b, e]).add(c, -1000).constant(-3));
f.hint(a, 1); f.hint(NOT(b), 1);
const mine = f.encode();
const ref = await CpSat.createModel(f.proto());
const schemas = await CpSat.getSchemas();
const T = protobuf.parse(schemas.cp_model).root.lookupType('operations_research.sat.CpModelProto');
const opts = { longs: String, enums: String, defaults: false };
const A = JSON.stringify(T.toObject(T.decode(mine), opts)), B = JSON.stringify(T.toObject(T.decode(ref), opts));
console.log(A === B ? 'KODLAMA AYNI' : 'KODLAMA FARKLI\n' + A + '\n' + B);
const r1 = await CpSat.solve(mine, { maxTimeInSeconds: 5 }), r2 = await CpSat.solve(ref, { maxTimeInSeconds: 5 });
console.log('çözüm', r1.response?.status, r1.response?.objectiveValue, '|', r2.response?.status, r2.response?.objectiveValue);
process.exit(0);
