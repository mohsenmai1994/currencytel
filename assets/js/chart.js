import {number,when} from './format.js';
export function drawHistory(svg,points,assetId){
  const empty=document.getElementById('chartEmpty');
  const entries=points.map(p=>({value:Number(p?.values?.[assetId]),date:p?.at})).filter(p=>Number.isFinite(p.value)&&p.value>0);
  svg.replaceChildren();
  if(entries.length<2){empty.hidden=false;return;}
  empty.hidden=true;
  const values=entries.map(e=>e.value);
  const min=Math.min(...values), max=Math.max(...values), range=Math.max(1e-9,max-min),width=640,height=190,pad=18;
  const pts=entries.map((e,i)=>({x:pad+i*(width-2*pad)/Math.max(1,entries.length-1), y:height-pad-(e.value-min)/range*(height-2*pad)}));
  const path=pts.map((p,i)=>`${i?'L':'M'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ');
  const NS='http://www.w3.org/2000/svg';
  const el=(name,attrs)=>{const n=document.createElementNS(NS,name);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,String(v)));return n;};
  const defs=el('defs',{}),grad=el('linearGradient',{id:'chartFill',x1:'0',y1:'0',x2:'0',y2:'1'});
  grad.append(el('stop',{offset:'0%','stop-color':'#56d3c2','stop-opacity':'.24'}),el('stop',{offset:'100%','stop-color':'#56d3c2','stop-opacity':'0'}));defs.append(grad);svg.append(defs);
  for(let i=0;i<4;i++)svg.append(el('line',{x1:pad,y1:pad+i*((height-pad*2)/3),x2:width-pad,y2:pad+i*((height-pad*2)/3),stroke:'currentColor','stroke-opacity':'.10','stroke-dasharray':'4,5'}));
  svg.append(el('path',{d:`${path} L${pts.at(-1).x},${height-pad} L${pad},${height-pad} Z`,fill:'url(#chartFill)'}));
  svg.append(el('path',{d:path,fill:'none',stroke:'#56d3c2','stroke-width':'3','stroke-linecap':'round','stroke-linejoin':'round'}));
  const last=pts.at(-1);svg.append(el('circle',{cx:last.x,cy:last.y,r:5,fill:'#56d3c2',stroke:'#0b1420','stroke-width':2}));
  const first=entries[0],end=entries.at(-1),diff=(end.value/first.value-1)*100;
  document.getElementById('chartMeta').textContent=`${entries.length.toLocaleString('fa-IR')} گزارش • ${when(first.date)} تا ${when(end.date)} • ${diff>=0?'+':''}${number(diff,2)}٪ تغییر در بازه ذخیره‌شده`;
}
