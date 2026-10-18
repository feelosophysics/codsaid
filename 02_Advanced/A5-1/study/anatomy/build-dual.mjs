import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {createHash} from 'node:crypto';
import * as k from './vendor/iso-kit.mjs';
import * as A from './vendor/audit.mjs';
const HERE=dirname(fileURLToPath(import.meta.url)),MISSION=join(HERE,'../..');
const raw=readFileSync(join(MISSION,'results/test_predictions.json')),src=JSON.parse(raw);
const dualRaw=readFileSync(join(MISSION,'results/dual_predictions.json')),dual=JSON.parse(dualRaw);
const classification=JSON.parse(readFileSync(join(MISSION,'results/metrics.json'))).classification.models[src.final].test;
if(createHash('sha256').update(raw).digest('hex')!==dual.source_sha256)throw Error('예측 원본이 달라졌습니다. export_dual_predictions.py를 다시 실행하세요.');
const data={features:src.features,rows:src.rows,actualCredit:src.credit_score,actualOverdue:src.is_overdue,credit:dual.regression_predictions,risk:src.proba[src.final],regressionModel:`Lasso · α=${dual.alpha}`,classificationModel:src.final,metrics:dual.metrics};
const P=k.fitProjection([...k.boxCorners({x:-210,y:-105,w:440,d:215,r:7},-10,6),[-180,-18,50],[200,100,24]],960,470,{pad:35,azimuth:62,elevation:42});
const R=A.recorder(P);let n=0;
const X=-76,SPAN=258;
function part(name,x,y,w,d,z,h,{piece='',lit=false,tone='mid',inner='',r=.7}={}){
 const plan={x,y,w,d,r},id=`d${n++}`;
 const shape=R.solid(A.slab(plan,z,h,{name,ground:name.startsWith('stand.')}));
 const move=piece?[SPAN,0,0]:[0,0,0];
 R.put({name,piece,id,at:[x+w/2,y+d/2,z+h/2],move,shapes:[shape],svg:`<g id="${id}" data-piece="${piece}">${k.solidSvg(k.slabOf(plan,z,h,P,8,Math.min(.5,h/4)),{tone,lit,inner})}</g>`});
}
function screw(name,x,y,z){part(name,x-1,y-1,2,2,z,.6,{r:.2,tone:'lo',inner:k.lineSvg(k.lineOnTop([x-1,y],[x+1,y],z+.6,P),{tone:'mid'})});}
for(const x of [-190,210])for(const y of [-85,90])part('stand.foot',x-6,y-6,12,12,-10,9,{tone:'lo',r:2});
part('stand.base',-210,-105,440,215,-1,7,{r:7});
part('deck',-205,-100,430,205,6,2,{r:5});
for(const x of [-194,214])for(const y of [-89,94])screw('base.screw',x,y,8);
// A single card reader is the shared input. Its two outputs are independent.
part('reader.foot',-184,-30,66,67,8,5,{r:3});
part('reader.body',-180,-26,58,59,13,12,{r:3});
part('reader.left-guide',-175,-19,6,43,25,6);
part('reader.right-guide',-133,-19,6,43,25,6);
part('reader.card',-168,-17,34,39,25,1,{lit:true});
for(let i=0;i<6;i++)part('reader.field',-164,-13+i*5.4,26,2.4,26,.4,{tone:'lo',r:.2});
for(const y of [-21,28])for(const x of [-174,-128])screw('reader.screw',x,y,25);
const rulerLabels=[];
function gauge(name,y,max){
 part(`${name}.support`,X-15,y-5,SPAN+30,61,8,5,{r:3});
 let ticks='';
 for(let i=0;i<=50;i++){
  const x=X+SPAN*i/50;
  ticks+=k.lineSvg(k.lineOnTop([x,y+40],[x,y+40+(i%5?3:6)],13.6,P),{tone:i%5?'lo':'mid'});
  if(i%10===0)ticks+=k.faceTextSvg(k.topMatrix([x,y+52],13.6,P,'x'),String(i/50*max),{size:4.6,anchor:'middle'});
 }
 part(`${name}.ruler`,X-5,y+40,SPAN+10,14,13,.6,{inner:ticks,r:.3});
 for(const lane of [y+3,y+21])part(`${name}.rail`,X-5,lane,SPAN+10,4,13,2,{r:.4});
 for(const x of [X-11,X+SPAN+7]){part(`${name}.stop`,x,y,4,30,13,5);screw(`${name}.stop.screw`,x+2,y+14,18);}
 rulerLabels.push(k.faceTextSvg(k.topMatrix([X+SPAN-3,y-1],13,P,'x'),name==='credit'?'0 – 1000':'0 – 1',{size:4.3,anchor:'end'}));
}
gauge('credit',-85,1000);gauge('risk',26,1);
function marker(name,y,piece,lit){
 part(`${name}.shoe`,X-3,y,6,6,15,2,{piece,lit});
 part(`${name}.flag`,X-1.4,y+.5,2.8,5,17,14,{piece,lit});
 part(`${name}.cap`,X-2,y,4,6,31,1,{piece,lit});
}
marker('credit.predicted',-82,'credit',true);
marker('credit.actual',-64,'actual',false);
marker('risk.predicted',29,'risk',true);
part('risk.threshold',X+SPAN*.5-1,47,2,4,15,8,{lit:false,tone:'hi'});
part('nameplate',-182,70,61,17,8,.6,{inner:k.faceTextSvg(k.topMatrix([-177,81],8.6,P,'x'),'TWO QUESTIONS',{size:3.4,tone:'mid'})});
part('service.panel',X,90,75,10,8,.5,{tone:'lo'});
for(const x of [X+3,X+72])screw('panel.screw',x,95,8.5);
const states=[];
for(const s of [0,.2,.5,.8,1])for(const a of [0,.3,.6,1])states.push({shares:{credit:s,actual:a,risk:1-s}});
A.settle(R,P,{states});A.auditOrExit(R,P,{frames:states,apart:false});
const items=R.items.sort((a,b)=>a.key-b.key);
const itemData=items.map(a=>({id:a.id,piece:a.piece,key:a.key,lift:a.move.reduce((s,v,i)=>s+v*R.V[i],0)}));
const svg=k.figureSvg({width:960,height:470,label:'고객 정보 카드 판독기 옆에 서로 독립된 두 계측기가 있다. 위쪽은 0에서 1000까지 신용 점수, 아래쪽은 0에서 1까지 연체 예측 점수를 읽는다.',body:[`<path class="iso-halo" d="${k.haloOf({x:-210,y:-105,w:440,d:215,r:7},-10,3,P)}"/>`,`<g id="dual-parts">${items.map(a=>a.svg).join('')}</g>`]});
const samples=[data.risk.findIndex((p,i)=>p<.05&&data.actualOverdue[i]===0),data.risk.findIndex((p,i)=>p>.8&&data.actualOverdue[i]===1),data.risk.map((p,i)=>({p,i})).filter(a=>data.actualOverdue[a.i]===1&&a.p<.5).sort((a,b)=>b.p-a.p)[0].i];
const live=`const DATA=${JSON.stringify(data)};const P=${JSON.stringify(P)};const ITEMS=${JSON.stringify(itemData)};const SAMPLES=${JSON.stringify(samples)};\n`+readFileSync(join(HERE,'dual.js'),'utf8');
const css=readFileSync(join(HERE,'style.css'),'utf8')+'\n'+readFileSync(join(HERE,'dual.css'),'utf8');
const html=`<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>A5-1 · 같은 고객, 두 가지 예측</title><style>${k.ISO_CSS}\n${css}</style><body class="iso" data-theme="light"><main>
<header><div class="eyebrow">A5-1 / CONCEPT LAB · 02</div><nav><a href="../a5-1.html#ch01" target="_blank" rel="noopener">종합 학습 자료 ↗</a><a href="threshold.html">임계값 실험</a><button id="theme">밝기 전환</button></nav><h1>같은 고객에게,<br><em>서로 다른 질문을 합니다.</em></h1><p class="intro">“신용 점수는 몇 점일까?”와 “연체할까?”<br>입력은 같아도, 배울 정답과 결과를 평가하는 방법은 달라집니다.</p></header>
<div class="context-strip"><span>이미 학습한 모델 2개</span><span>학습용 8,000명 → 평가용 2,000명</span><span>지금은 평가용 고객을 살펴봅니다</span></div>
<section class="customer-picker"><div><label for="customer-select">설명할 고객 선택 <span id="customer-id"></span></label><select id="customer-select" aria-label="Test 고객 선택"></select></div><div class="presets"><button data-sample="0">고객 A</button><button data-sample="1">고객 B</button><button data-sample="2">고객 C</button><button id="next-customer">다음 고객 →</button></div></section>
<section class="inputs"><div><div class="eyebrow">두 모델에 함께 주는 입력</div><h2>우리가 아는 고객 정보 6개</h2><p class="small">실제 신용 점수와 연체 여부는 입력에 넣지 않습니다.</p></div><dl id="features"></dl></section>
<div class="teaching-actions"><button id="predict" class="primary">① 두 모델로 예측하기</button><button id="reveal" disabled>② 정답 공개하고 비교하기</button><button id="reset">처음부터 설명하기</button><span id="phase" role="status" aria-live="polite">먼저 두 질문의 답이 어떤 형태일지 예상해 보세요.</span></div>
<div class="dual-layout"><section class="lab"><div class="iso-plate"><div class="card-head"><span>FIG. 02</span><span>고객 하나 · 독립된 계측기 둘</span></div><div id="dual-stage" tabindex="0" role="group" aria-label="두 가지 예측 장치. Enter 키로 예측, R 키로 정답 공개, 좌우 방향키로 고객 변경">${svg}</div><div class="card-foot"><span>카드 = 같은 입력 · 위 = 회귀 · 아래 = 분류</span><span data-readout>아직 예측 전</span></div></div><p class="caption">한 고객의 정보를 두 모델이 각각 읽습니다. 위 계측기의 결과를 아래 계측기에 넣는 구조가 아닙니다. 이동하는 표시자는 <b>이미 계산한 예측값</b>을 보여주는 비유입니다.</p><div class="legend"><span><i class="gate-key"></i>밝은 표시자 = 예측</span><span>위의 두 번째 표시자 = 공개한 실제 점수</span><span>아래 고정 표식 = 판정 기준 0.5</span></div></section>
<section class="answers"><article class="answer regression"><div class="eyebrow">질문 1 / 회귀</div><h2>신용 점수는 몇 점일까?</h2><div class="model-name">Lasso · α=0.1 · 학습할 정답: 신용 점수</div><div class="reading"><span id="reg-value">—</span><small>점 / 0~1000</small></div><div class="truth" id="reg-truth" hidden></div><p class="small">숫자를 예측합니다. 정답과의 <b>차이가 얼마나 작은지</b> 평가합니다.</p></article><article class="answer classification"><div class="eyebrow">질문 2 / 분류</div><h2>연체할까?</h2><div class="model-name">RF + class_weight · 학습할 정답: 연체 여부</div><div class="reading"><span id="risk-value">—</span><small>예측 점수 / 0~1</small></div><div class="decision" id="decision">0.5 이상이면 연체로 예측</div><div class="truth" id="risk-truth" hidden></div><p class="small">범주를 구분합니다. 점수에 기준을 적용한 뒤 <b>누구를 맞히고 놓쳤는지</b> 평가합니다.</p></article></section></div>
<section id="evaluation" class="evaluation" hidden><div class="eyebrow">고객 한 명의 결과 ≠ 모델 전체의 성능</div><h2>같은 ‘잘 예측했다’도, 재는 방법이 다릅니다.</h2><div class="evaluation-grid"><article><h3>회귀 · 오차 크기</h3><p>이 고객의 오차: <strong id="single-error"></strong></p><p>평가용 2,000명 전체:<br>MAE <b>${dual.metrics.mae.toFixed(2)}점</b> · RMSE <b>${dual.metrics.rmse.toFixed(2)}점</b> · R² <b>${dual.metrics.r2.toFixed(3)}</b></p><p class="small">MAE는 오차 절댓값의 평균, RMSE는 큰 오차에 더 민감한 척도입니다.</p></article><article><h3>분류 · 실수의 종류</h3><p>이 고객의 결과: <strong id="single-class"></strong></p><p>평가용 2,000명 전체, 기준 0.5:<br>Precision <b>${(classification.precision*100).toFixed(1)}%</b> · Recall <b>${(classification.recall*100).toFixed(1)}%</b> · F1 <b>${(classification.f1*100).toFixed(1)}%</b></p><p class="small">기준을 바꾸면 분류 판정이 바뀝니다. <a href="threshold.html">임계값 분류기로 이어서 보기 →</a></p></article></div></section>
<section class="learning"><div><div class="eyebrow">초보자에게 이렇게 설명해 보세요</div><h2>설명 순서: 입력 → 질문 → 예측 → 정답 → 평가</h2><ol><li>“이 고객의 정보 6개를 두 모델에 똑같이 줍니다.”</li><li>“한 모델은 점수를, 다른 모델은 연체 여부를 배우도록 학습했습니다.”</li><li>예측 버튼을 누른 뒤 “출력의 단위가 어떻게 다른가요?”라고 묻습니다.</li><li>정답을 공개하고 숫자의 오차와 분류의 실수를 각각 짚습니다.</li><li>고객 C에서도 설명이 유지되는지 확인합니다.</li></ol></div><div><div class="eyebrow">스스로 확인할 질문</div><h2>신용 점수를 잘 맞히면 연체도 반드시 맞힐까요?</h2><details><summary>먼저 설명한 뒤 펼쳐 보세요</summary><p>반드시 그렇지는 않습니다. 두 모델은 서로 다른 정답으로 학습하고, 연체 여부에는 생성 과정의 무작위성도 있습니다. 회귀 오차가 작아도 분류 기준 근처에서는 판정이 달라질 수 있습니다. 이 구현의 분류기는 회귀 예측값을 입력받지 않습니다.</p></details><p class="small">두 장면은 미션의 회귀·분류·판정 차이를 설명합니다. 전처리, 데이터 누수 방지, 규제, 불균형 처리와 모델 선택은 <a href="../a5-1.html" target="_blank" rel="noopener">종합 학습 자료</a>에서 이어집니다.</p></div></section>
<footer><p>A5-1의 합성 금융 데이터와 실제 구현의 Test 예측 결과입니다. 실존 고객 자료가 아닙니다. 모델 출력은 개인의 보정된 실제 연체 확률로 검증하지 않았습니다.</p><p>고객 정보 6개에서 파생 변수·전처리를 거쳐 각 모델이 예측합니다. 장치는 이 내부 계산을 기계 구조로 그대로 재현한 것이 아니라 입력·출력 관계를 설명하는 비유입니다. 모델을 바꾸거나 화면에서 새로 학습하지 않습니다.</p><p>Anatomy · MIT · 오프라인 HTML · Enter: 예측 / R: 정답 공개 / ← →: 고객 변경</p></footer></main><script>${live}</script></body></html>`;
writeFileSync(join(HERE,'two-predictions.html'),html);
writeFileSync(join(HERE,'dual-manifest.json'),JSON.stringify({source:'results/test_predictions.json',sourceSha256:dual.source_sha256,dualSha256:createHash('sha256').update(dualRaw).digest('hex'),rows:data.rows.length,parts:n,samples,regressionModel:data.regressionModel,classificationModel:data.classificationModel,regressionMetrics:dual.metrics,geometryStates:states.length},null,2));
console.log(`Built two-predictions.html: ${n} solids, ${data.rows.length} rows, ${Buffer.byteLength(html)} bytes`);
