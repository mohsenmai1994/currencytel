import {createGlobe} from './world-globe.js';
import {METRICS,getIndicator,getReferenceFx,displayMetric,displayFx} from './world-service.js';
const $=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
let cachedCountries;
async function countries(){
  if(!cachedCountries)cachedCountries=fetch('./assets/data/world-countries.json').then(async r=>{
    if(!r.ok)throw new Error('فهرست کشورها بارگیری نشد');const payload=await r.json();
    if(!Array.isArray(payload?.countries)||payload.countries.length<100)throw new Error('فهرست کشورها ناقص است');
    return payload.countries;
  }).catch(error=>{cachedCountries=null;throw error;});
  return cachedCountries;
}
export async function mountWorldEconomy(target){
  target.replaceChildren();let disposed=false,activeRequest=null,globe=null;
  const root=$('div','ctmf-world');
  const intro=$('p','ctmf-intro','کره زمین را بچرخانید و کشور را لمس کنید؛ یا از فهرست، کشور موردنظر را انتخاب کنید. شاخص‌ها بر اساس آخرین داده منتشرشده هستند.');
  const grid=$('div','ctmf-world-grid'),globePanel=$('section','ctmf-globe-panel'),globeHost=$('div','ctmf-globe-host');
  const controls=$('div','ctmf-globe-controls'),zoomIn=$('button','ctmf-mini-btn','+'),zoomOut=$('button','ctmf-mini-btn','−');
  zoomIn.type=zoomOut.type='button';zoomIn.setAttribute('aria-label','بزرگ‌نمایی کره');zoomOut.setAttribute('aria-label','کوچک‌نمایی کره');
  controls.append(zoomIn,zoomOut);globePanel.append(globeHost,controls,$('p','ctmf-globe-tip','برای چرخاندن کره، انگشت را روی آن بکشید.'));
  const info=$('section','ctmf-country-panel');const label=$('label','ctmf-field'),labelText=$('span','ctmf-field-label','انتخاب کشور'),selector=$('select','ctmf-input');
  selector.setAttribute('aria-label','انتخاب کشور');label.append(labelText,selector);
  const countryName=$('h3','ctmf-country-title',''),currency=$('div','ctmf-currency'),updated=$('p','ctmf-muted','');
  const metrics=$('div','ctmf-indicator-grid'),cells={};
  for(const [key,descriptor] of Object.entries(METRICS)){
    const card=$('div','ctmf-indicator'),small=$('small','',descriptor.title),value=$('strong','', '—'),year=$('span','ctmf-indicator-year','');
    card.append(small,value,year);metrics.append(card);cells[key]={value,year};
  }
  const fxTitle=$('small','ctmf-field-label','نرخ مرجع ارز کشور'),fxValue=$('strong','', '—'),fxDate=$('span','ctmf-muted','');
  currency.append(fxTitle,fxValue,fxDate);
  const foot=$('p','ctmf-source-note','منبع شاخص‌ها: بانک جهانی (World Bank). نرخ مرجع ارز: Frankfurter. این داده‌ها معادل نرخ بازار آزاد ایران یا قیمت لحظه‌ای نیستند.');
  const links=$('div','ctmf-source-links');links.innerHTML='<a href="https://data.worldbank.org/" target="_blank" rel="noopener noreferrer">بانک جهانی ↗</a><a href="https://frankfurter.dev/" target="_blank" rel="noopener noreferrer">منبع نرخ ارز ↗</a>';
  info.append(label,countryName,updated,currency,metrics,foot,links);grid.append(globePanel,info);root.append(intro,grid);target.append(root);
  let listed;
  try{
    listed=await countries();
    if(disposed)return ()=>{};
  }catch{globeHost.textContent='نقشه فعلاً در دسترس نیست.';countryName.textContent='فهرست کشورها بارگیری نشد. اتصال را بررسی کنید.';return ()=>root.remove();}
  const countryByCode=new Map(listed.map(c=>[c.code,c]));
  const sorted=[...listed].sort((a,b)=>a.name.localeCompare(b.name,'fa'));
  for(const c of sorted){const opt=$('option','',c.name);opt.value=c.code;selector.append(opt);}
  async function selectCountry(code,{rotate=true}={}){
    const c=countryByCode.get(code);if(!c||disposed)return;
    if(activeRequest)activeRequest.abort();const controller=new AbortController();activeRequest=controller;
    selector.value=code;countryName.textContent=`${c.name} · ${c.code}`;
    updated.textContent='در حال دریافت تازه‌ترین آمار منتشرشده…';
    fxValue.textContent=c.currency?`۱ دلار آمریکا = … ${c.currency}`:'واحد پول مشخص نیست';fxDate.textContent='';
    for(const part of Object.values(cells)){part.value.textContent='…';part.year.textContent='';}
    if(rotate)globe?.setCountry(code);
    const keys=Object.keys(METRICS);
    const promises=keys.map(key=>getIndicator(code,key,{signal:controller.signal}).then(data=>{
      if(disposed||controller.signal.aborted)return;
      const el=cells[key];el.value.textContent=data?displayMetric(data.value,METRICS[key].type):'ناموجود';
      el.year.textContent=data?`آخرین سال: ${data.year}`:'داده‌ای منتشر نشده';
    }).catch(()=>{
      if(disposed||controller.signal.aborted)return;
      cells[key].value.textContent='در دسترس نیست';cells[key].year.textContent='خطا در دریافت داده';
    }));
    promises.push(getReferenceFx(c.currency,{signal:controller.signal}).then(rate=>{
      if(disposed||controller.signal.aborted)return;
      fxValue.textContent=rate?`۱ دلار آمریکا = ${displayFx(rate.value,c.currency)}`:`نرخ مرجع ${c.currency||'این ارز'} در دسترس نیست`;
      fxDate.textContent=rate?.date?`تاریخ نرخ: ${rate.date}`:c.currency==='USD'?'نسبت ثابت (دلار به دلار)':'در صورت نیاز، نرخ رسمی را جداگانه بررسی کنید.';
    }).catch(()=>{if(disposed||controller.signal.aborted)return;fxValue.textContent=`نرخ مرجع ${c.currency||'این ارز'} در دسترس نیست`;fxDate.textContent='منبع نرخ پاسخ نداد یا این ارز پشتیبانی نمی‌شود.';}));
    await Promise.allSettled(promises);
    if(!disposed&&!controller.signal.aborted)updated.textContent='آخرین داده‌های موجود؛ سال هر شاخص در کنار آن درج شده است.';
  }
  selector.addEventListener('change',()=>selectCountry(selector.value));
  try{
    globe=createGlobe(globeHost,listed,{initialCode:'IR',onCountry:code=>selectCountry(code,{rotate:false})});
    zoomIn.addEventListener('click',()=>globe?.zoomBy(.1));zoomOut.addEventListener('click',()=>globe?.zoomBy(-.1));
  }catch{globeHost.textContent='نمایش کره روی این دستگاه پشتیبانی نمی‌شود؛ کشور را از فهرست انتخاب کنید.';controls.hidden=true;}
  selectCountry('IR');
  return ()=>{disposed=true;activeRequest?.abort();globe?.destroy();root.remove();};
}
