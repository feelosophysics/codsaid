// 학습 자료의 JavaScript 계산을 Python(scikit-learn) 기준값과 대조한다.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const page = fs.readFileSync(path.join(root, 'study/a5-1.html'), 'utf8');
const script = id => {
  const m = page.match(new RegExp(`<script id="${id}"[^>]*>([\\s\\S]*?)<\\/script>`));
  assert.ok(m, `script ${id} 없음`);
  return m[1];
};
const ctx = vm.createContext({});
new vm.Script(script('math-engine')).runInContext(ctx);
new vm.Script(script('guide-ui')); // 문법 검사. DOM 동작은 브라우저에서 확인한다.
const M = ctx.a5Math;
const data = JSON.parse(script('guide-data'));
const ev = JSON.parse(fs.readFileSync(path.join(root, 'study/calculation-evidence.json'), 'utf8'));
const close = (a, b, label) => assert.ok(Math.abs(a - b) < 1e-9, `${label}: ${a} != ${b}`);
const plain = v => JSON.parse(JSON.stringify(v));
let cases = 0;

function check(actual, expected, label) {
  assert.deepEqual(plain(actual.confusion), expected.confusion, `${label} confusion`);
  for (const k of ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']) close(actual[k], expected[k], `${label} ${k}`);
  cases++;
}
for (const c of ev.rule_cases) check(M.ruleEval(data, c.rules), c, `rules ${c.rules}`);
for (const r of data.rules) {
  const hits = M.ruleScore(data.rows, data.features, [r], [r.id]).filter(s => s > 0).length;
  assert.equal(hits, ev.rule_hit_counts[r.id], `hits ${r.id}`); cases++;
}
for (const c of ev.threshold_cases) check(M.thresholdEval(data.proba[c.model], data.y, c.threshold), c, `${c.model}@${c.threshold}`);
for (const c of ev.band_cases) {
  assert.deepEqual(plain(M.bands(data.proba[data.final], data.y, c.hold, c.reject)), c.bands, `bands ${c.hold}/${c.reject}`); cases++;
}
// 저장된 모델 지표(임계값 0.5, scikit-learn predict)와 페이지 계산이 같은지.
// 페이지의 확률은 소수점 6자리로 반올림해 저장했으므로, 반올림으로 생긴 동점 때문에 AUC가 1e-5 안에서 달라질 수 있다.
for (const [name, p] of Object.entries(data.proba)) {
  const t = data.models[name].test;
  const m = M.thresholdEval(p, data.y, 0.5);
  assert.ok(Math.abs(m.roc_auc - t.roc_auc) < 1e-5, `${name} auc: ${m.roc_auc} != ${t.roc_auc}`);
  assert.deepEqual(plain(m.confusion), t.confusion, `${name} confusion@0.5`); cases++;
}
const base = M.ruleEval(data, data.rules.map(r => r.id));
assert.deepEqual(plain(base.confusion), data.models['Rule baseline'].test.confusion); cases++;
close(M.auc([1, 2, 2, 3], [0, 0, 1, 1]), 0.875, 'tie auc'); cases++;
console.log(JSON.stringify({ passed: true, python_comparison_cases: cases }));
