const $=id=>document.getElementById(id);
const still=matchMedia('(prefers-reduced-motion: reduce)');
const nodes=ITEMS.map(item=>({...item,node:$(item.id)}));
const labels=['나이','연 소득','소비 점수','부채 비율','카드 수','최근 6개월 연체 횟수'];
let selected=SAMPLES[0],phase=0,shown={credit:0,risk:0},target={credit:0,risk:0},frame=0,last=0,visible=true;
const select=$('customer-select');
DATA.rows.forEach((_,i)=>{const option=document.createElement('option');option.value=i;option.textContent='Test #'+String(i+1).padStart(4,'0');select.appendChild(option);});
function format(value,index){if(index===0)return value+'세';if(index===1)return value.toLocaleString('ko-KR')+'만원';if(index===3)return (value*100).toFixed(0)+'%';if(index===4)return value+'장';if(index===5)return value+'회';return value+'점';}
function settled(){return shown.credit===target.credit&&shown.risk===target.risk;}
function translate(share){const a=P.azimuth*Math.PI/180,e=P.elevation*Math.PI/180,k=P.scale*Math.sqrt(1.6);return `translate(${258*share*Math.sin(a)*k} ${258*share*Math.cos(a)*Math.sin(e)*k})`;}
function draw(){
 const shares={credit:shown.credit,risk:shown.risk,actual:DATA.actualCredit[selected]/1000};
 nodes.forEach(item=>{if(item.piece){item.node.setAttribute('transform',translate(shares[item.piece]));item.node.style.display=item.piece==='actual'?(phase===2?'':'none'):(phase>=1?'':'none');}});
 const group=$('dual-parts');[...nodes].sort((a,b)=>(a.key+a.lift*(shares[a.piece]??0))-(b.key+b.lift*(shares[b.piece]??0))).forEach(item=>group.appendChild(item.node));
 const ready=phase>=1&&settled();
 $('reveal').disabled=!ready||phase===2;
 $('reg-value').textContent=ready?DATA.credit[selected].toFixed(1):phase?'…':'—';
 $('risk-value').textContent=ready?DATA.risk[selected].toFixed(3):phase?'…':'—';
 $('decision').textContent=ready?`${DATA.risk[selected].toFixed(6)} ${DATA.risk[selected]>=.5?'≥':'<'} 0.5 → ${DATA.risk[selected]>=.5?'연체':'정상'} 예측`:'0.5 이상이면 연체로 예측';
 document.querySelector('[data-readout]').textContent=phase===0?'아직 예측 전':!ready?'표시자 이동 중':phase===2?'정답과 비교':'두 가지 예측';
 document.body.dataset.phase=phase;document.body.dataset.ready=String(ready);document.body.dataset.selected=selected;
}
function tick(now){frame=0;if(!visible||document.hidden)return;const dt=last?Math.min((now-last)/1000,1/30):1/60;last=now;for(const key of ['credit','risk']){shown[key]=still.matches?target[key]:shown[key]+(target[key]-shown[key])*(1-Math.exp(-dt/.18));if(Math.abs(shown[key]-target[key])<.00001)shown[key]=target[key];}draw();if(!settled())run();}
function run(){if(!frame&&visible&&!document.hidden)frame=requestAnimationFrame(tick);}
function choose(i){selected=(Number(i)+DATA.rows.length)%DATA.rows.length;phase=0;shown={credit:0,risk:0};target={credit:0,risk:0};select.value=selected;$('customer-id').textContent='Test #'+String(selected+1).padStart(4,'0');$('features').replaceChildren();DATA.rows[selected].forEach((value,index)=>{const div=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=labels[index];dd.textContent=format(value,index);div.append(dt,dd);$('features').appendChild(div);});for(const id of ['reg-truth','risk-truth','evaluation'])$(id).hidden=true;$('predict').disabled=false;$('phase').textContent='먼저 두 질문의 답이 어떤 형태일지 예상해 보세요.';draw();}
function predict(){if(phase!==0)return;phase=1;target={credit:DATA.credit[selected]/1000,risk:DATA.risk[selected]};$('predict').disabled=true;$('phase').textContent='같은 입력에서 서로 다른 단위의 출력이 나옵니다. 정답을 공개해 비교해 보세요.';if(still.matches){shown={...target};draw();}else{last=0;run();}draw();}
function reveal(){if(phase!==1||!settled())return;phase=2;const actual=DATA.actualCredit[selected],pred=DATA.credit[selected],error=pred-actual,actualOverdue=DATA.actualOverdue[selected],positive=DATA.risk[selected]>=.5;const result=actualOverdue?(positive?'TP · 연체자를 잡음':'FN · 연체자를 놓침'):(positive?'FP · 정상 고객을 잘못 잡음':'TN · 정상 고객을 맞힘');$('reg-truth').textContent=`실제 ${actual}점 · 예측 ${pred.toFixed(1)}점 · ${Math.abs(error).toFixed(1)}점 ${error>=0?'높게':'낮게'} 예측`;$('risk-truth').textContent=`실제 ${actualOverdue?'연체':'정상'} · ${result}`;$('single-error').textContent=Math.abs(error).toFixed(1)+'점';$('single-class').textContent=result;for(const id of ['reg-truth','risk-truth','evaluation'])$(id).hidden=false;$('phase').textContent='회귀는 숫자의 오차를, 분류는 맞힘과 실수의 종류를 비교합니다.';draw();}
select.addEventListener('change',event=>choose(event.target.value));
document.querySelectorAll('[data-sample]').forEach(button=>button.addEventListener('click',()=>choose(SAMPLES[Number(button.dataset.sample)])));
$('next-customer').addEventListener('click',()=>choose(selected+1));$('predict').addEventListener('click',predict);$('reveal').addEventListener('click',reveal);$('reset').addEventListener('click',()=>choose(selected));
$('theme').addEventListener('click',()=>document.body.dataset.theme=document.body.dataset.theme==='light'?'dark':'light');
$('dual-stage').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();predict();}if(e.key.toLowerCase()==='r'){e.preventDefault();reveal();}if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();choose(selected+(e.key==='ArrowRight'?1:-1));}});
new IntersectionObserver(entries=>{visible=entries.at(-1).isIntersecting;if(visible){last=0;run();}}).observe($('dual-stage'));
document.addEventListener('visibilitychange',()=>{last=0;if(!document.hidden)run();});
still.addEventListener('change',()=>{if(still.matches){shown={...target};draw();}});
window.__dualChoose=choose;
choose(selected);
