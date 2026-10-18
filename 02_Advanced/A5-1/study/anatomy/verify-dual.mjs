import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const HERE=dirname(fileURLToPath(import.meta.url)),MISSION=join(HERE,'../..');
const raw=readFileSync(join(MISSION,'results/test_predictions.json')),source=JSON.parse(raw);
const dualRaw=readFileSync(join(MISSION,'results/dual_predictions.json')),dual=JSON.parse(dualRaw);
const manifest=JSON.parse(readFileSync(join(HERE,'dual-manifest.json')));
const metrics=JSON.parse(readFileSync(join(MISSION,'results/metrics.json')));
assert.equal(createHash('sha256').update(raw).digest('hex'),dual.source_sha256);
assert.equal(manifest.sourceSha256,dual.source_sha256);
assert.equal(manifest.dualSha256,createHash('sha256').update(dualRaw).digest('hex'));
const html=readFileSync(join(HERE,'two-predictions.html'),'utf8');
const embedded=JSON.parse(html.match(/const DATA=(.*?);const P=/s)[1]);
assert.deepEqual(embedded.features,source.features);assert.deepEqual(embedded.rows,source.rows);
assert.deepEqual(embedded.actualCredit,source.credit_score);assert.deepEqual(embedded.actualOverdue,source.is_overdue);
assert.deepEqual(embedded.credit,dual.regression_predictions);assert.deepEqual(embedded.risk,source.proba[source.final]);
assert.equal(embedded.rows.length,2000);assert.equal(new Set(dual.test_row_indices).size,2000);
assert.ok(embedded.credit.every(v=>Number.isFinite(v)&&v>=0&&v<=1000),'regression gauge range');
assert.ok(embedded.risk.every(v=>Number.isFinite(v)&&v>=0&&v<=1),'classification gauge range');
assert.equal(dual.regression_model,'Lasso');assert.equal(dual.alpha,metrics.regression.comparison.Lasso.alpha);
const mean=embedded.actualCredit.reduce((a,b)=>a+b,0)/2000;
const errors=embedded.credit.map((v,i)=>v-embedded.actualCredit[i]);
const mse=errors.reduce((a,b)=>a+b*b,0)/2000;
const observed={rmse:Math.sqrt(mse),mae:errors.reduce((a,b)=>a+Math.abs(b),0)/2000,r2:1-errors.reduce((a,b)=>a+b*b,0)/embedded.actualCredit.reduce((a,b)=>a+(b-mean)**2,0)};
for(const key of Object.keys(observed))assert.ok(Math.abs(observed[key]-metrics.regression.comparison.Lasso.test[key])<1e-9,`regression ${key}`);
const [a,b,c]=manifest.samples;assert.equal(source.is_overdue[a],0);assert.ok(embedded.risk[a]<.05);assert.equal(source.is_overdue[b],1);assert.ok(embedded.risk[b]>.8);assert.equal(source.is_overdue[c],1);assert.ok(embedded.risk[c]<.5);
let links=0;
for(const name of ['two-predictions.html','threshold.html']){
 const page=readFileSync(join(HERE,name),'utf8');
 assert.ok(!/<script[^>]+src=|<link[^>]+href=["']https?:|https?:\/\//i.test(page.replaceAll('http://www.w3.org/2000/svg','')),'no external runtime dependency');
 for(const match of page.matchAll(/href="([^"#]+)(?:#[^"]*)?"/g)){const target=match[1];if(/^[a-z]+:/i.test(target))continue;assert.ok(existsSync(resolve(HERE,target)),`broken link ${name}: ${target}`);links++;}
 assert.ok(!page.includes('existing-a5-1.html'),'no old guide copy link');
}
writeFileSync(join(HERE,'dual-verification.json'),JSON.stringify({records:2000,dataArraysIdentical:true,sourceHashesMatch:true,regressionMetrics:observed,referenceMetricsMatch:true,teachingExamplesValidated:true,localLinks:links,offline:true},null,2));
console.log(`PASS: 2,000 rows, both model outputs and true targets match sources; regression metrics match; ${links} local links valid; no old copies or remote dependencies`);
