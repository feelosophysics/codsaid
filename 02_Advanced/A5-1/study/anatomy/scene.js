const $=id=>document.getElementById(id);
const still=matchMedia('(prefers-reduced-motion: reduce)');
const nodes=ITEMS.map(item=>({...item,node:$(item.id)}));
const baseline=classify(DATA.labels,DATA.scores,.5);
let threshold=.5,target=.5,selected=INITIAL,frame=0,last=0,visible=true,touring=false,tourTime=0,lastTourStep=-1;
const clamp=v=>Math.max(0,Math.min(1,v));
function delta(n){return n>0?'+'+n:String(n);}
function transform(share){const [x,y]=project([350*share,0,0]),[ox,oy]=P.origin;return `translate(${x-ox} ${y-oy})`;}
function project([x,y,z]){const a=P.azimuth*Math.PI/180,e=P.elevation*Math.PI/180,k=P.scale*Math.sqrt(1.6);return [P.origin[0]+(x*Math.sin(a)-y*Math.cos(a))*k,P.origin[1]+((x*Math.cos(a)+y*Math.sin(a))*Math.sin(e)-z*Math.cos(e))*k];}
function stopTour(){touring=false;$('tour').setAttribute('aria-pressed','false');$('tour').textContent='자동 비교';}
function setTarget(v,user=true){if(user)stopTour();target=clamp(Number(v));$('threshold').value=String(target);$('target').textContent=target.toFixed(3);$('stage').setAttribute('aria-valuenow',String(target));$('stage').setAttribute('aria-valuetext','분류 임계값 '+target.toFixed(3));if(still.matches){threshold=target;draw();}else run();}
function draw(){
 const m=classify(DATA.labels,DATA.scores,threshold),p=DATA.scores[selected],actual=DATA.labels[selected],positive=p>=threshold;
 nodes.forEach(i=>{if(i.piece)i.node.setAttribute('transform',transform(i.piece==='gate'?threshold:p));});
 const ordered=[...nodes].sort((a,b)=>(a.key+a.lift*(a.piece==='gate'?threshold:a.piece==='card'?p:0))-(b.key+b.lift*(b.piece==='gate'?threshold:b.piece==='card'?p:0)));
 const group=$('parts');ordered.forEach(i=>group.appendChild(i.node));
 for(const key of ['tp','fp','tn','fn'])$(key).textContent=m[key].toLocaleString('ko-KR');
 for(const key of ['precision','recall','f1'])$(key).textContent=(m[key]*100).toFixed(1)+'%';
 $('precision-fraction').textContent=`${m.tp} / ${m.tp+m.fp}명`;
 $('recall-fraction').textContent=`${m.tp} / 240명`;
 document.querySelector('[data-readout]').textContent='임계값 '+threshold.toFixed(3);
 $('customer').textContent=`Test #${String(selected+1).padStart(4,'0')} · 실제 ${actual?'연체':'정상'} · 예측 점수 ${p.toFixed(6)}`;
 $('comparison').textContent=`${p.toFixed(6)} ${positive?'≥':'<'} ${threshold.toFixed(3)} → ${positive?'연체':'정상'} 예측 · ${actual?(positive?'TP · 잡음':'FN · 놓침'):(positive?'FP · 잘못 잡음':'TN · 정상 통과')}`;
 $('comparison').dataset.correct=String(Boolean(actual)===positive);
 $('delta').textContent=`기본 기준 0.5와 비교하면, 잡은 연체자 ${delta(m.tp-baseline.tp)}명 · 잘못 잡은 정상 고객 ${delta(m.fp-baseline.fp)}명입니다.`;
 document.body.dataset.threshold=threshold.toFixed(6);document.body.dataset.selected=selected;
 window.__result=m;
}
function tick(now){
 frame=0;if(!visible||document.hidden)return;
 const dt=last?Math.min((now-last)/1000,1/30):1/60;last=now;
 if(touring){tourTime+=dt;const step=Math.floor(tourTime/3.5)%3;if(step!==lastTourStep){lastTourStep=step;setTarget([.2,.5,.8][step],false);}}
 threshold=still.matches?target:threshold+(target-threshold)*(1-Math.exp(-dt/.17));
 if(Math.abs(threshold-target)<.00001)threshold=target;
 draw();if(touring||threshold!==target)run();
}
function run(){if(!frame&&visible&&!document.hidden)frame=requestAnimationFrame(tick);}
$('threshold').addEventListener('input',event=>setTarget(event.target.value));
document.querySelectorAll('[data-t]').forEach(b=>b.addEventListener('click',()=>setTarget(b.dataset.t)));
$('stage').addEventListener('keydown',e=>{let next;if(e.key==='ArrowRight'||e.key==='ArrowUp')next=target+.01;else if(e.key==='ArrowLeft'||e.key==='ArrowDown')next=target-.01;else if(e.key==='Home')next=0;else if(e.key==='End')next=1;else return;e.preventDefault();setTarget(next);});
let dragging=false;
function steer(e){const svg=$('stage').querySelector('svg'),matrix=svg.getScreenCTM(),pt=new DOMPoint(e.clientX,e.clientY).matrixTransform(matrix.inverse());const origin=project([-175,1,49]),end=project([175,1,49]),vx=end[0]-origin[0],vy=end[1]-origin[1];setTarget(((pt.x-origin[0])*vx+(pt.y-origin[1])*vy)/(vx*vx+vy*vy));}
$('stage').addEventListener('pointerdown',e=>{if(e.button!==0)return;dragging=true;$('stage').setPointerCapture(e.pointerId);steer(e);});
$('stage').addEventListener('pointermove',e=>{if(dragging)steer(e);});
for(const event of ['pointerup','pointercancel'])$('stage').addEventListener(event,e=>{dragging=false;if($('stage').hasPointerCapture(e.pointerId))$('stage').releasePointerCapture(e.pointerId);});
function choose(kind){stopTour();let candidates=DATA.scores.map((p,i)=>({p,i}));if(kind==='missed')candidates=candidates.filter(o=>DATA.labels[o.i]&&o.p<threshold);if(kind==='false')candidates=candidates.filter(o=>!DATA.labels[o.i]&&o.p>=threshold);candidates.sort((a,b)=>Math.abs(a.p-threshold)-Math.abs(b.p-threshold));if(candidates.length){selected=candidates[0].i;$('customer-note').textContent='실제 라벨은 검사선을 움직여도 바뀌지 않습니다.';}else $('customer-note').textContent='현재 임계값에는 이 조건에 해당하는 고객이 없습니다.';draw();}
$('near').addEventListener('click',()=>choose('near'));
$('missed').addEventListener('click',()=>choose('missed'));
$('false').addEventListener('click',()=>choose('false'));
$('next').addEventListener('click',()=>{stopTour();selected=(selected+1)%DATA.labels.length;draw();});
$('tour').addEventListener('click',()=>{if(touring){stopTour();return;}touring=true;tourTime=0;lastTourStep=-1;$('tour').textContent='자동 비교 정지';$('tour').setAttribute('aria-pressed','true');run();});
$('theme').addEventListener('click',()=>document.body.dataset.theme=document.body.dataset.theme==='light'?'dark':'light');
new IntersectionObserver(entries=>{visible=entries.at(-1).isIntersecting;if(visible){last=0;run();}}).observe($('stage'));
document.addEventListener('visibilitychange',()=>{last=0;if(!document.hidden)run();});
still.addEventListener('change',()=>{if(still.matches){stopTour();threshold=target;draw();}});
window.__setThreshold=v=>setTarget(v);
window.__classify=t=>classify(DATA.labels,DATA.scores,t);
draw();
