// Cross-check browser math against values computed by actual Python analysis.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'study/a1-1.html'), 'utf8');
const extract = id => {
  const match = html.match(new RegExp(`<script id="${id}"[^>]*>([\\s\\S]*?)<\\/script>`));
  assert.ok(match, `Missing script ${id}`);
  return match[1];
};
const context = vm.createContext({});
new vm.Script(extract('math-engine')).runInContext(context);
new vm.Script(extract('guide-ui')); // Syntax-check UI; browser exercises its DOM wiring.
const math = context.a1Math;
const data = JSON.parse(extract('guide-data'));
const evidence = JSON.parse(fs.readFileSync(path.join(root, 'study/calculation-evidence.json'), 'utf8'));
const plain = value => JSON.parse(JSON.stringify(value));
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-8, `${actual} != ${expected}`);
let cases = 0;
for (const c of evidence.tiny_cases) {
  const actual = math.tinyRfm(data.tiny, c.reference);
  const expected = c.expected.map(({customer_id, recency, frequency, monetary}) => ({customer_id, recency, frequency, monetary}));
  assert.deepEqual(plain(actual), expected); cases++;
}
assert.equal(math.tinyRfm(data.tiny, '2026-10-10', 'rows')[0].frequency, 3); cases++;
assert.throws(() => math.tinyRfm(data.tiny, '2026-10-08')); cases++;
for (const c of evidence.segment_cases) {
  const counts = plain(math.segmentCounts(data.rfm, c.recent, c.inactive, c.loyal, data.vip_cutoff));
  for (const [name, count] of Object.entries(counts)) assert.equal(count, c.expected[name] ?? 0);
  assert.equal(Object.values(counts).reduce((a,b)=>a+b,0), 240); cases++;
}
// Check every score and group, rather than just matching aggregate counts.
const r = math.scores(data.rfm.map(row=>row.recency), false);
const f = math.scores(data.rfm.map(row=>row.frequency), true);
const m = math.scores(data.rfm.map(row=>row.monetary), true);
data.rfm.forEach((row,i)=>{
  assert.equal(r[i], row.r_score); assert.equal(f[i], row.f_score); assert.equal(m[i], row.m_score);
  assert.equal(math.segment(row,30,90,4,data.vip_cutoff), row.segment);
}); cases++;
for (const c of evidence.iqr_cases) {
  const actual = math.iqrStats(c.high, c.threshold);
  close(actual.lower, c.lower); close(actual.upper, c.upper);
  assert.deepEqual(plain(actual.flagged), c.flagged); assert.deepEqual(plain(actual.clipped), c.clipped); cases++;
}
for (const c of evidence.image_cases) {
  const actual = math.imageStats(c.brightness, c.contrast, c.pattern);
  close(actual.mean, c.mean); close(actual.std, c.std); assert.deepEqual(plain(actual.pixels), c.pixels); cases++;
}
for (const c of evidence.imputation_cases) {
  const actual = math.imputation(c.repeat, c.strategy);
  close(actual.correct, c.correct); close(actual.weighted, c.weighted); cases++;
}
assert.deepEqual(plain(math.scores([1,10,10],false)),[5,3,3]); cases++;
assert.equal(math.segment({recency:150,frequency:8,monetary:3e6},30,90,4,data.vip_cutoff),'Inactive'); cases++;
console.log(JSON.stringify({passed:true,python_comparison_cases:cases,customer_scores_and_groups:240}));
