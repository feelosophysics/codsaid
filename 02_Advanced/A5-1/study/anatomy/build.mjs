import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {join,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import * as k from './vendor/iso-kit.mjs';
import * as A from './vendor/audit.mjs';
import {classify} from './model.mjs';
const HERE=dirname(fileURLToPath(import.meta.url));
const SOURCE=join(HERE,'../..');
const raw=readFileSync(join(SOURCE,'results/test_predictions.json'));
const predictions=JSON.parse(raw), model=predictions.final;
const data={model,labels:predictions.is_overdue,scores:predictions.proba[model]};
const metrics=JSON.parse(readFileSync(join(SOURCE,'results/metrics.json')));
const theme=process.argv.includes('--dark')?'dark':'light';
const P=k.fitProjection([...k.boxCorners({x:-210,y:-75,w:430,d:175,r:6},-10,8),[-180,-40,65],[180,55,65]],900,430,{pad:42,azimuth:65,elevation:34});
const R=A.recorder(P), x0=-175, span=350;
let part=0;
function slab(name,x,y,w,d,z,h,{piece='',lit=false,tone='mid',r=0.7,inner='',cls=''}={}) {
  const plan={x,y,w,d,r}, id=`p${part++}`;
  const shape=R.solid(A.slab(plan,z,h,{name,ground:name.startsWith('stand.')}));
  const move=piece?[span,0,0]:[0,0,0];
  const svg=`<g id="${id}" data-piece="${piece}" class="${cls}">${k.solidSvg(k.slabOf(plan,z,h,P,8,Math.min(.4,h/4)),{tone,lit,inner})}</g>`;
  R.put({name,piece,at:[x+w/2,y+d/2,z+h/2],move,svg,shapes:[shape],id});
}
function screw(name,x,y,z,piece=''){slab(name,x-1.1,y-1.1,2.2,2.2,z,.65,{piece,r:.25,tone:'lo',inner:k.lineSvg(k.lineOnTop([x-1,y],[x+1,y],z+.65,P),{tone:'mid'})});}
// Base, feet, surface and maintained panel.
for(const x of [-190,190]) for(const y of [-55,80]) slab('stand.foot',x-7,y-7,14,14,-10,8,{tone:'lo',r:2});
slab('stand.base',-210,-75,430,175,-2,8,{r:6});
slab('deck',-205,-70,420,165,6,2,{r:4});
for(const x of [-198,198])for(const y of [-62,87])screw('base.screw',x,y,8);
slab('nameplate',-165,78,88,11,8,.6,{tone:'lo',inner:k.faceTextSvg(k.topMatrix([-160,85],8.6,P,'x'),'A5 / THRESHOLD',{size:4,tone:'mid'})});
slab('service.panel',105,73,72,17,8,.6,{tone:'lo'});
for(const x of [110,172])for(const y of [76,87])screw('panel.screw',x,y,8.6);
for(let i=0;i<5;i++)slab('panel.slot',120+i*8,77,2,9,8.6,.25,{tone:'lo',r:.4});
// Two parallel tracks, travel stops and square fasteners.
for(const y of [-43,47]){
  slab('track',-190,y,380,7,8,4,{r:1});
  for(const x of [-197,190]){
    slab('stop',x,y-3,7,13,8,10,{r:1});
    screw('stop.screw',x+3.5,y+3.5,18);
  }
  for(const x of [-180,-60,60,180])screw('track.mount.screw',x,y-4,8);
}
// Ruler is rooted at the strip edge; all digits lie on the surface.
let scaleMarks='';
for(let i=0;i<=50;i++){
 const x=x0+span*i/50;
 scaleMarks+=k.lineSvg(k.lineOnTop([x,60],[x,60+(i%5===0?6:3)],8.5,P),{tone:i%5?'lo':'mid'});
 if(i%5===0)scaleMarks+=k.faceTextSvg(k.topMatrix([x,71],8.5,P,'x'),(i/50).toFixed(1),{size:4,anchor:'middle'});
}
slab('ruler',-180,60,360,14,8,.5,{r:.3,inner:scaleMarks});
slab('card.track',-190,-10,380,20,8,3,{r:1,tone:'lo'});
// Gate: shoes sit on rails, columns flank the card, crossbeam clears its top.
for(const y of [-43,47]){
 slab('gate.shoe',x0-6,y-1,12,9,12,3,{piece:'gate'});
 slab('gate.column',x0-3,y+1,6,5,15,30,{piece:'gate',lit:true});
 for(const dx of [-4,4])screw('gate.screw',x0+dx,y+3.5,15,'gate');
}
slab('gate.crossbeam',x0-4,-42,8,95,45,5,{piece:'gate',lit:true});
slab('gate.cap',x0-5,-43,10,97,50,1.5,{piece:'gate'});
slab('gate.handle.base',x0-5,-8,10,20,51.5,3,{piece:'gate'});
slab('gate.handle',x0-4,-6,8,16,54.5,5,{piece:'gate',lit:true});
for(let i=0;i<6;i++)slab('gate.grip',x0-3.5,-5+i*2.5,7,.6,59.5,.4,{piece:'gate',tone:'lo',r:.1});
// One selected customer's score card; every metric uses all 2,000 records.
slab('card.foot',x0-5,-8,10,16,11,3,{piece:'card'});
slab('card',x0-2,-7,4,14,14,18,{piece:'card',tone:'hi',cls:'customer-card'});
slab('card.label',x0-1.5,-6,3,12,32,.4,{piece:'card',tone:'hi'});
slab('card.notch',x0-1,-3,2,6,32.4,.4,{piece:'card',lit:true});
// Both translations are real motions, not explode effects. Solve their depth keys together.
const states=[];
for(const gate of [0,.1,.2,.35,.5,.65,.8,.9,1])for(const card of [0,.01,.19,.49,.51,.8,1])states.push({shares:{gate,card}});
A.settle(R,P,{states});
A.auditOrExit(R,P,{frames:states,apart:false});
const items=R.items.sort((a,b)=>A.keyAt(a,{shares:{gate:.5,card:.5}},R.V)-A.keyAt(b,{shares:{gate:.5,card:.5}},R.V));
const svg=k.figureSvg({width:900,height:430,label:'0에서 1까지의 예측 점수 눈금 위를 움직이는 문형 검사대와 고객 카드. 고객 점수가 검사선 이상이면 연체로 예측한다.',body:[`<path class="iso-halo" d="${k.haloOf({x:-210,y:-75,w:430,d:175,r:6},-10,2,P)}"/>`,`<g id="parts">${items.map(a=>a.svg).join('')}</g>`]});
const itemData=items.map(a=>({id:a.id,piece:a.piece,key:a.key,lift:a.move.reduce((sum,v,i)=>sum+v*R.V[i],0)}));
const initial=data.scores.map((p,i)=>({p,i})).filter(v=>data.labels[v.i]===1).sort((a,b)=>Math.abs(a.p-.5)-Math.abs(b.p-.5))[0].i;
const script=`const DATA=${JSON.stringify(data)};const P=${JSON.stringify(P)};const ITEMS=${JSON.stringify(itemData)};const INITIAL=${initial};const classify=${classify.toString()};\n`+readFileSync(join(HERE,'scene.js'),'utf8');
const existing=readFileSync(join(SOURCE,'study/a5-1.html'));
const css=readFileSync(join(HERE,'style.css'),'utf8');
const html=`<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>A5-1 · 움직이는 검사선</title><style>${k.ISO_CSS}\n${css}</style><body class="iso" data-theme="${theme}"><main>
<header><div class="eyebrow">A5-1 / CONCEPT LAB · 01</div><nav><a href="../a5-1.html#ch04" target="_blank" rel="noopener">기존 학습 자료 ↗</a><a href="two-predictions.html">회귀·분류 장면</a><button id="theme" type="button">밝기 전환</button></nav><h1>기준을 옮기면,<br><em>어떤 실수가 달라질까?</em></h1><p class="intro">모델의 점수는 그대로입니다. 연체로 판단하는 <b>검사선</b>만 옮겨 보세요.</p></header>
<div class="layout"><section class="lab"><div class="iso-plate"><div class="card-head"><span>FIG. 01</span><span>움직이는 검사선</span></div><div class="stage" id="stage" tabindex="0" role="slider" aria-label="분류 임계값. 좌우 화살표로 0.01씩 조절" aria-valuemin="0" aria-valuemax="1" aria-valuenow="0.5">${svg}</div><div class="card-foot"><span>← 낮은 점수 · 높은 점수 →</span><span data-readout>임계값 0.500</span></div></div>
<div class="legend"><span><i class="gate-key"></i>문형 검사대 = 임계값 t</span><span><i class="card-key"></i>작은 카드 = 선택한 고객의 점수 p</span></div>
<div class="control"><label for="threshold">연체로 판단하는 기준 <output id="target">0.500</output></label><input id="threshold" type="range" min="0" max="1" step="0.001" value="0.5"><div class="presets"><button data-t="0.2">0.2 · 더 넓게 잡기</button><button data-t="0.5">0.5 · 기본 기준</button><button data-t="0.8">0.8 · 더 엄격하게</button><button id="tour" aria-pressed="false">자동 비교</button></div></div>
<article class="customer"><div class="eyebrow">확대해서 보는 고객 1명</div><p id="customer"></p><p class="formula" id="comparison"></p><div class="presets"><button id="near">검사선 근처 고객</button><button id="missed">놓친 연체자 보기</button><button id="false">잘못 잡은 정상 고객</button><button id="next">다음 고객</button></div><p class="small" id="customer-note">실제 라벨은 검사선을 움직여도 바뀌지 않습니다.</p></article></section>
<aside><div class="eyebrow">같은 TEST 2,000명 전체</div><h2>누구를 잡고, 누구를 놓쳤나</h2><p class="small">RF + class_weight · 실제 연체 240명 / 정상 1,760명</p><table class="matrix"><caption class="sr">임계값에 따른 혼동 행렬</caption><thead><tr><th scope="col">실제 ↓ / 예측 →</th><th scope="col">정상 예측</th><th scope="col">연체 예측</th></tr></thead><tbody><tr><th scope="row">정상<br><small>1,760명</small></th><td class="correct"><strong id="tn"></strong><span>TN · 정상 통과</span></td><td class="mistake"><strong id="fp"></strong><span>FP · 잘못 잡음</span></td></tr><tr><th scope="row">연체<br><small>240명</small></th><td class="mistake"><strong id="fn"></strong><span>FN · 놓침</span></td><td class="correct"><strong id="tp"></strong><span>TP · 잡음</span></td></tr></tbody></table>
<div class="scores"><div><span>Precision · 잡은 고객 중 실제 연체</span><b id="precision"></b><small id="precision-fraction"></small></div><div><span>Recall · 실제 연체 중 잡은 비율</span><b id="recall"></b><small id="recall-fraction"></small></div><div><span>F1 · Precision과 Recall의 조화평균</span><b id="f1"></b></div></div><p id="delta" class="insight"></p><p class="small">모두 정상으로 예측해도 정확도는 88%입니다. 그래서 잡은 수와 놓친 수를 함께 봅니다.</p></aside></div>
<section class="learning"><div><div class="eyebrow">움직이기 전에 예상하기</div><h2>0.5에서 0.2로 낮추면?</h2><p>‘놓친 연체자’와 ‘잘못 잡은 정상 고객’은 각각 늘어날까요, 줄어들까요? 먼저 예상하고 손잡이를 움직여 확인해 보세요.</p><details><summary>확인 후 설명 읽기</summary><p>검사선을 낮추면 연체로 예측하는 범위가 넓어져 FN은 늘지 않고 FP는 줄지 않습니다. Recall은 낮아지지 않지만 Precision이 반드시 낮아지는 것은 아닙니다. 이 데이터의 실제 값으로 확인하세요. F1은 두 지표를 함께 반영하므로 한 방향으로만 움직이지 않습니다.</p></details></div><div><div class="eyebrow">기존 자료와 비교하기</div><h2>그림 없이도 설명할 수 있나요?</h2><p><a href="../a5-1.html#ch04" target="_blank" rel="noopener">기존 자료의 ‘04 분류 지표’ 열기 ↗</a> → 같은 RF + class_weight 모델과 임계값 0.2·0.5·0.8을 비교하세요.</p><p>장면을 가리고 “임계값을 올릴 때 왜 놓치는 연체자가 늘 수 있는가”를 설명해 보세요. 검사대의 모양보다 <b>p ≥ t라는 판정 규칙</b>이 떠오르는지가 비교 기준입니다.</p></div></section>
<footer><p>A5-1에서 생성한 가상 금융 고객의 저장된 Test 예측 결과입니다. 장치는 이미 계산된 점수에 기준을 적용하는 비유입니다. 실제 금융 고객의 자료가 아닙니다. Test를 조작하는 이 실험으로 운영 임계값을 선택하지 않습니다.</p><p>선택한 고객 1명은 확대 예시이며 모든 지표는 2,000명 전체로 계산합니다. 모델 출력의 확률 보정은 검증하지 않았습니다. 지표의 분모가 0일 때는 0으로 표시합니다.</p><p>Anatomy · MIT · 오프라인 HTML · 방향키 또는 슬라이더로 조작 · 자동 비교는 버튼으로 정지</p></footer></main><script>${script}</script></body></html>`;
writeFileSync(join(HERE,theme==='light'?'threshold.html':'threshold-dark.html'),html);
writeFileSync(join(HERE,'source-manifest.json'),JSON.stringify({date:'2026-10-18',skillCommit:'e9488296a44211c42701ff71705b7901470ec78f',model,records:data.labels.length,positives:data.labels.reduce((a,b)=>a+b,0),source:'results/test_predictions.json',sha256:createHash('sha256').update(raw).digest('hex'),existingGuideSha256:createHash('sha256').update(existing).digest('hex'),parts:part,baseline:classify(data.labels,data.scores,.5),reference:metrics.classification.models[model].test},null,2));
console.log(`Built ${theme}: ${part} solids, ${data.labels.length} customers, ${Buffer.byteLength(html)} bytes`);
