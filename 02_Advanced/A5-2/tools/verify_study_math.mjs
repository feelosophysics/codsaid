// 학습 자료의 JavaScript 계산을 Python(scikit-learn, shap) 결과와 대조한다.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const page = fs.readFileSync(path.join(root, 'study/a5-2.html'), 'utf8');
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
const close = (a, b, tol, label) => assert.ok(Math.abs(a - b) < tol, `${label}: ${a} != ${b}`);
let cases = 0;

// 1. 저장된 평균·표준편차·중심으로 다시 계산한 군집이 scikit-learn K-Means 배정과 같은가
const clusters = M.assign(data.rows, data.transform);
clusters.forEach((c, i) => assert.equal(c, data.cluster[i], `cluster ${i}`));
cases += clusters.length;
// 2. PCA 투영이 scikit-learn PCA 좌표와 같은가(저장 좌표는 소수점 5자리)
data.rows.forEach((r, i) => {
  const p = M.project(M.scale(r, data.transform), data.transform);
  close(p[0], data.pca[i][0], 1e-4, `pc1 ${i}`); close(p[1], data.pca[i][1], 1e-4, `pc2 ${i}`);
});
cases += data.rows.length;
// 3. SHAP 가법성: 기준값 + SHAP 합 = 모델 확률(저장 값은 소수점 6자리 반올림)
data.shap.forEach((s, i) => close(M.reconstruct(data.base_value, s), data.proba[i], 1e-5, `additivity ${i}`));
cases += data.shap.length;
// 4. 거리 실험
for (const c of ev.distance_cases) {
  const d = M.distance(data.rows[c.a], data.rows[c.b], data.transform);
  close(d.raw, c.raw, 1e-9, 'raw'); close(d.scaled, c.scaled, 1e-9, 'scaled');
  c.raw_share.forEach((v, j) => close(d.raw_share[j], v, 1e-12, 'raw share'));
  c.scaled_share.forEach((v, j) => close(d.scaled_share[j], v, 1e-12, 'scaled share'));
  cases++;
}
// 5. Shapley 장난감: 순열 평균(Python itertools)과 같은가, 효율성(합 = v(ABC) − v(∅))
for (const t of ev.toy_games) {
  const s = M.shapley3(t.game);
  for (const p of 'ABC') close(s[p], t.shapley[p], 1e-12, `shapley ${p}`);
  close(s.A + s.B + s.C, t.game.ABC - t.game[''], 1e-12, 'efficiency');
  cases++;
}
// 6. K 선택 규칙이 Python select_k와 같은 결과를 내는가
const sel = M.selectK(data.scan, data.selection.distinguishing_features, data.min_ari);
for (const k of ['best_silhouette_k', 'within_one_se', 'stable', 'final_k']) {
  assert.deepEqual(JSON.parse(JSON.stringify(sel[k])), ev.selection[k], `selectK ${k}`);
}
close(sel.cutoff, ev.selection.cutoff, 1e-12, 'cutoff'); cases++;
console.log(JSON.stringify({ passed: true, python_comparison_cases: cases }));
