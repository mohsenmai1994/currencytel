import {number,when} from './format.js';
import {historyWindow,PERIODS} from './history.js';

const NS = 'http://www.w3.org/2000/svg';
const node = (tag, attrs = {}, text = null) => {
  const el = document.createElementNS(NS, tag);
  for (const [key,val] of Object.entries(attrs)) el.setAttribute(key, String(val));
  if (text !== null) el.textContent = String(text);
  return el;
};
const clamp = (v,lo,hi) => Math.min(hi,Math.max(lo,v));
const axisNumber = value => Math.abs(value)>=1000 ? new Intl.NumberFormat('fa-IR',{notation:'compact',maximumFractionDigits:2}).format(value) : number(value,2);
const chartDate = (ms,range,full=false) => new Intl.DateTimeFormat('fa-IR',{
  timeZone:'Asia/Tehran',
  ...(full ? {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}
           : range==='24h' ? {hour:'2-digit',minute:'2-digit'} : {month:'short',day:'numeric'}),
}).format(new Date(ms));
const pointsAsPath = entries => entries.map((p,i)=>`${i?'L':'M'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');

/** Responsive, accessible SVG chart of actual stored observations only.
 * Can render both full analysis and compact detail-sheet views.
 * Returns the computed data window for independent KPI rendering.
 */
export function drawHistory(svg,history,assetId,options={}){
  const range = PERIODS[options.range] ? options.range : '24h';
  const model = historyWindow(history,assetId,range);
  const compact=Boolean(options.compact);
  const wrap=svg.parentElement;
  const width=Math.round(clamp(wrap?.clientWidth||600,240,1150));
  const height=compact?110:(width<440?250:286);
  const left=compact?7:(width<440?57:72),right=compact?7:19,top=compact?10:18,bottom=compact?10:38;
  const pw=width-left-right,ph=height-top-bottom;
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
  svg.style.height=`${height}px`;
  svg.replaceChildren();
  if (options.emptyEl) options.emptyEl.hidden=model.entries.length>0;
  const tooltip=options.tooltipEl;
  if (tooltip) tooltip.hidden=true;
  if (!model.entries.length) {
    svg.onpointermove=null;svg.onpointerleave=null;svg.onkeydown=null;svg.onfocus=null;
    return model;
  }
  const vals=model.entries.map(p=>p.value);
  const lo=model.min,hi=model.max;
  const span=Math.max(hi-lo,Math.abs(hi)*.00012,1e-8);
  const yMin=lo-span*.18,yMax=hi+span*.18;
  const x=t=>left+clamp((t-model.start)/(model.end-model.start),0,1)*pw;
  const y=v=>top+ph-(v-yMin)/(yMax-yMin)*ph;
  const fillColor=model.difference===null?'#5daec8':model.difference<0?'#f07d90':'#4bceb4';
  if(!compact){
    for(let i=0;i<4;i++){
      const yy=top+ph*i/3;
      svg.append(node('line',{x1:left,y1:yy,x2:width-right,y2:yy,stroke:'currentColor','stroke-opacity':'.12','stroke-dasharray':'3 5'}));
      svg.append(node('text',{x:left-8,y:yy+4,fill:'currentColor','fill-opacity':'.65','font-size':10,'text-anchor':'end','font-family':'Vazirmatn, sans-serif'},axisNumber(yMax-(yMax-yMin)*i/3)));
    }
    for(let i=0;i<=3;i++){
      const t=model.start+(model.end-model.start)*i/3;
      const px=left+pw*i/3;
      svg.append(node('text',{x:px,y:height-12,fill:'currentColor','fill-opacity':'.65','font-size':10,'text-anchor':i===0?'start':i===3?'end':'middle','font-family':'Vazirmatn, sans-serif'},chartDate(t,range)));
    }
  }
  const pts=model.entries.map(p=>({...p,x:x(p.t),y:y(p.value)}));
  // Break lines over large missing intervals. The chart must not imply prices
  // continuously existed during outages of the source or collector.
  const gapThreshold=({'24h':2,'7d':12,'30d':48,'90d':96})[range]*3600000;
  const segments=[];
  let segment=[];
  for(const p of pts){
    if(segment.length && p.t-segment.at(-1).t>gapThreshold){segments.push(segment);segment=[];}
    segment.push(p);
  }
  if(segment.length)segments.push(segment);
  for(const group of segments){
    const path=pointsAsPath(group);
    if(group.length>1){
      const base=top+ph;
      svg.append(node('path',{d:`${path} L ${group.at(-1).x.toFixed(1)} ${base} L ${group[0].x.toFixed(1)} ${base} Z`,fill:fillColor,'fill-opacity':compact?'.09':'.13'}));
      svg.append(node('path',{d:path,fill:'none',stroke:fillColor,'stroke-width':compact?2:2.75,'stroke-linejoin':'round','stroke-linecap':'round'}));
    } else {
      svg.append(node('circle',{cx:group[0].x,cy:group[0].y,r:compact?2.5:3.5,fill:fillColor}));
    }
  }
  if(!compact){
    const last=pts.at(-1);
    svg.append(node('circle',{cx:last.x,cy:last.y,r:5,fill:fillColor,stroke:'#0c1726','stroke-width':2}));
  }
  if (compact) return model;

  const line=node('line',{x1:0,y1:top,x2:0,y2:top+ph,stroke:fillColor,'stroke-width':1,'stroke-dasharray':'4 4'});
  const spot=node('circle',{cx:0,cy:0,r:5,fill:fillColor,stroke:'#fff','stroke-width':2});
  line.style.display='none';spot.style.display='none';svg.append(line,spot);
  let focused=-1;
  const displayAt=(i,clientX=null)=>{
    if(!pts.length || !tooltip)return;
    focused=clamp(i,0,pts.length-1);
    const p=pts[focused];line.setAttribute('x1',p.x);line.setAttribute('x2',p.x);
    spot.setAttribute('cx',p.x);spot.setAttribute('cy',p.y);
    line.style.display='';spot.style.display='';
    tooltip.replaceChildren();
    const price=document.createElement('strong');price.textContent=number(p.value,4);
    const date=document.createElement('span');date.textContent=chartDate(p.t,range,true);
    tooltip.append(price,date);tooltip.hidden=false;
    const box=wrap.getBoundingClientRect();
    const xPx=clientX!==null ? clientX-box.left : p.x;
    tooltip.style.left=`${clamp(xPx,75,Math.max(75,box.width-75))}px`;
    tooltip.style.top=`${clamp(p.y-65,4,height-75)}px`;
    svg.setAttribute('aria-label',`نمودار ${PERIODS[range].label}؛ ${date.textContent}، قیمت ${price.textContent}`);
  };
  svg.onpointermove=event=>{
    const rect=svg.getBoundingClientRect();
    const pos=(event.clientX-rect.left)*width/rect.width;
    let low=0,high=pts.length;
    while(low<high){const middle=(low+high)>>1;if(pts[middle].x<pos)low=middle+1;else high=middle;}
    const i=low<=0?0:low>=pts.length?pts.length-1:Math.abs(pts[low].x-pos)<Math.abs(pts[low-1].x-pos)?low:low-1;
    displayAt(i,event.clientX);
  };
  svg.onpointerleave=()=>{line.style.display='none';spot.style.display='none';if(tooltip)tooltip.hidden=true;};
  svg.onfocus=()=>displayAt(focused>=0?focused:pts.length-1);
  svg.onkeydown=event=>{
    if(!['ArrowLeft','ArrowRight','Home','End','Escape'].includes(event.key))return;
    event.preventDefault();
    if(event.key==='Escape'){svg.onpointerleave();return;}
    const i=event.key==='Home'?0:event.key==='End'?pts.length-1:clamp((focused>=0?focused:pts.length-1)+(event.key==='ArrowLeft'?-1:1),0,pts.length-1);
    displayAt(i);
  };
  return model;
}
