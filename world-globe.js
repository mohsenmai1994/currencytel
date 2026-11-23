/** Orthographic 3D globe renderer, self-contained Canvas, including country hit-testing.
 * Country polygons are local simplified Natural Earth geometry, no remote CDN.
 */
const rad=Math.PI/180;
const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
export function createGlobe(host,countries,{onCountry,initialCode='IR'}={}) {
  const canvas=document.createElement('canvas');
  canvas.className='ctmf-globe-canvas';canvas.tabIndex=0;
  canvas.setAttribute('role','img');
  canvas.setAttribute('aria-label','کره سه‌بعدی تعاملی؛ برای چرخش انگشت بکشید یا از فهرست کشورها استفاده کنید.');
  host.replaceChildren(canvas);
  const ctx=canvas.getContext('2d');
  if(!ctx)throw new Error('مرورگر امکان رسم کره را ندارد.');
  let destroyed=false,raf=0,w=0,h=0,radius=1,zoom=1,lat=31,lon=54,selected=initialCode;
  let drag=null,hit=[],focusCountry=null;
  const pointers=new Map();
  function project(geoLon,geoLat){
    const l=(geoLon-lon)*rad,p=geoLat*rad,cl=lat*rad;
    const cosP=Math.cos(p),cosC=Math.cos(cl),sinC=Math.sin(cl);
    return {x:cosP*Math.sin(l),y:cosC*Math.sin(p)-sinC*cosP*Math.cos(l),z:sinC*Math.sin(p)+cosC*cosP*Math.cos(l)};
  }
  const xy=pt=>[w/2+pt.x*radius,h/2-pt.y*radius];
  function cut(a,b){let left=a,right=b;
    for(let i=0;i<14;i++){
      const mid=[(left[0]+right[0])/2,(left[1]+right[1])/2];
      const v=project(mid[0],mid[1]);
      if((v.z>=0)===(project(left[0],left[1]).z>=0))left=mid;else right=mid;
    }
    return project((left[0]+right[0])/2,(left[1]+right[1])/2);
  }
  function drawRing(path,ring){
    if(ring.length<3)return false;
    let drawn=false,open=false;
    for(let i=0;i<ring.length-1;i++){
      const a=ring[i],b=ring[i+1],pa=project(a[0],a[1]),pb=project(b[0],b[1]);
      const va=pa.z>=0,vb=pb.z>=0;
      if(va&&!open){const [sx,sy]=xy(pa);path.moveTo(sx,sy);open=true;drawn=true;}
      if(va&&vb){const [sx,sy]=xy(pb);path.lineTo(sx,sy);}
      else if(va&&!vb){const [sx,sy]=xy(cut(a,b));path.lineTo(sx,sy);open=false;}
      else if(!va&&vb){const [sx,sy]=xy(cut(a,b));path.moveTo(sx,sy);const [ex,ey]=xy(pb);path.lineTo(ex,ey);open=true;drawn=true;}
    }
    return drawn;
  }
  function linePath(samples){
    const p=new Path2D();let active=false;
    for(const [a,b] of samples){const s=project(a,b);
      if(s.z<0){active=false;continue;}
      const [x,y]=xy(s);if(!active){p.moveTo(x,y);active=true;}else p.lineTo(x,y);
    }
    return p;
  }
  function colors(){const light=document.body.classList.contains('light');return light?
    {ocean:'#d2eceb',shade:'#7eaeb2',land:'#9bc8c2',stroke:'rgba(6,83,91,.57)',grid:'rgba(7,102,117,.16)',selected:'#07877d'}:
    {ocean:'#0a3547',shade:'#06111c',land:'#17626a',stroke:'rgba(97,207,196,.32)',grid:'rgba(97,207,196,.13)',selected:'#55d1c0'};}
  function render(){raf=0;if(destroyed)return;
    const b=canvas.getBoundingClientRect();if(b.width<50||b.height<50)return;
    w=b.width;h=b.height;
    const dpr=Math.min(window.devicePixelRatio||1,2);
    const px=Math.max(1,Math.round(w*dpr)),py=Math.max(1,Math.round(h*dpr));
    if(canvas.width!==px||canvas.height!==py){canvas.width=px;canvas.height=py;}
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
    radius=Math.max(40,Math.min(w*.47,h*.45)*zoom);
    const c=colors();
    ctx.save();ctx.shadowColor='rgba(65,218,204,.35)';ctx.shadowBlur=26;ctx.beginPath();ctx.arc(w/2,h/2,radius,0,Math.PI*2);ctx.fillStyle=c.ocean;ctx.fill();ctx.restore();
    ctx.save();ctx.beginPath();ctx.arc(w/2,h/2,radius,0,Math.PI*2);ctx.clip();
    const gradient=ctx.createRadialGradient(w/2-radius*.45,h/2-radius*.5,radius*.05,w/2+radius*.13,h/2+radius*.19,radius*1.23);
    gradient.addColorStop(0,c.ocean);gradient.addColorStop(1,c.shade);ctx.fillStyle=gradient;ctx.fillRect(w/2-radius,h/2-radius,radius*2,radius*2);
    for(let phi=-75;phi<=75;phi+=15){const p=[];for(let ll=-180;ll<=180;ll+=3)p.push([ll,phi]);ctx.strokeStyle=c.grid;ctx.lineWidth=.8;ctx.stroke(linePath(p));}
    for(let ll=-180;ll<180;ll+=20){const p=[];for(let phi=-90;phi<=90;phi+=3)p.push([ll,phi]);ctx.strokeStyle=c.grid;ctx.lineWidth=.8;ctx.stroke(linePath(p));}
    hit=[];
    for(const country of countries){const path=new Path2D();let drawn=false;
      for(const ring of country.rings||[]){if(drawRing(path,ring))drawn=true;}
      if(!drawn)continue;
      ctx.fillStyle=country.code===selected?c.selected:c.land;ctx.fill(path,'evenodd');
      ctx.strokeStyle=country.code===selected?c.selected:c.stroke;ctx.lineWidth=country.code===selected?1.8:.65;ctx.stroke(path);
      hit.push({country,path});
    }
    ctx.restore();
    ctx.beginPath();ctx.arc(w/2,h/2,radius,0,Math.PI*2);ctx.strokeStyle='rgba(85,209,192,.38)';ctx.lineWidth=1.5;ctx.stroke();
    const country=countries.find(x=>x.code===selected);
    if(country){let point=null;
      // Use a visible polygon vertex near screen center to locate a small focus dot.
      let dist=Infinity;
      for(const ring of country.rings||[])for(const [a,b] of ring){const pt=project(a,b);if(pt.z<.3)continue;const d=pt.x*pt.x+pt.y*pt.y;if(d<dist){dist=d;point=xy(pt);}}
      if(point){ctx.beginPath();ctx.arc(point[0],point[1],4,0,Math.PI*2);ctx.fillStyle='#e8fffb';ctx.fill();ctx.strokeStyle='#058f83';ctx.lineWidth=2;ctx.stroke();}
    }
  }
  const schedule=()=>{if(!raf&&!destroyed)raf=requestAnimationFrame(render);};
  const onResize=()=>schedule();
  const ro=typeof ResizeObserver!=='undefined'?new ResizeObserver(onResize):null;
  ro?.observe(canvas);window.addEventListener('resize',onResize);
  function setCountry(code){
    const country=countries.find(c=>c.code===code);if(!country)return;
    selected=code;
    // The geographic center of the largest ring, correcting for dateline wraps.
    const polygon=[...(country.rings||[])].sort((a,b)=>b.length-a.length)[0]||[];
    if(polygon.length){
      let sx=0,sy=0,sz=0;
      for(const [a,b] of polygon){const aa=a*rad,bb=b*rad;sx+=Math.cos(bb)*Math.cos(aa);sy+=Math.cos(bb)*Math.sin(aa);sz+=Math.sin(bb);}
      const n=polygon.length;const length=Math.hypot(sx,sy);
      if(length>0.001){lon=Math.atan2(sy,sx)/rad;lat=clamp(Math.atan2(sz,length)/rad,-75,75);}
    }
    schedule();
  }
  function at(x,y){
    const dpr=canvas.width/Math.max(1,w);
    for(let i=hit.length-1;i>=0;i--)if(ctx.isPointInPath(hit[i].path,x*dpr,y*dpr,'evenodd'))return hit[i].country;
    return null;
  }
  function coords(event){const box=canvas.getBoundingClientRect();return {x:event.clientX-box.left,y:event.clientY-box.top};}
  const down=event=>{if(event.button!==undefined&&event.button!==0)return;event.preventDefault();canvas.setPointerCapture?.(event.pointerId);
    pointers.set(event.pointerId,coords(event));drag={pointer:event.pointerId,from:coords(event),lon,lat,moved:false};canvas.classList.add('dragging');};
  const move=event=>{const p=coords(event);if(!pointers.has(event.pointerId))return;pointers.set(event.pointerId,p);
    if(!drag||drag.pointer!==event.pointerId)return;const dx=p.x-drag.from.x,dy=p.y-drag.from.y;
    if(Math.abs(dx)+Math.abs(dy)>5)drag.moved=true;
    if(drag.moved){lon=((drag.lon-dx*.32+540)%360)-180;lat=clamp(drag.lat+dy*.27,-80,80);schedule();}
  };
  const up=event=>{const p=coords(event);pointers.delete(event.pointerId);
    if(drag&&drag.pointer===event.pointerId){
      if(!drag.moved){const country=at(p.x,p.y);if(country){selected=country.code;onCountry?.(country.code);}}
      drag=null;canvas.classList.remove('dragging');schedule();
    }
  };
  const wheel=event=>{event.preventDefault();zoom=clamp(zoom+(event.deltaY<0?.08:-.08),.75,1.18);schedule();};
  const keys=event=>{if(!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.key))return;event.preventDefault();
    if(event.key==='ArrowLeft')lon-=12;if(event.key==='ArrowRight')lon+=12;
    if(event.key==='ArrowUp')lat=clamp(lat+9,-80,80);if(event.key==='ArrowDown')lat=clamp(lat-9,-80,80);
    schedule();};
  canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointermove',move);
  canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);
  canvas.addEventListener('wheel',wheel,{passive:false});canvas.addEventListener('keydown',keys);
  setCountry(initialCode);schedule();
  return {setCountry,zoomBy(delta){zoom=clamp(zoom+delta,.75,1.18);schedule();},destroy(){destroyed=true;if(raf)cancelAnimationFrame(raf);ro?.disconnect();window.removeEventListener('resize',onResize);canvas.remove();}};
}
