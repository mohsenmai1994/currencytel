/** CurrencyTel Ads: read-only public renderer. Never contains admin credentials. */
const ALLOWED_SLOTS = new Set([
  'home_quick','market_between','market_inline','news_inline',
  'world_footer','gold_footer','tools_footer','channels_footer'
]);
const $all = sel => Array.from(document.querySelectorAll(sel));
let current = null;
let loading = null;
let lastFetch = 0;
const REFRESH_MS = 5 * 60 * 1000;
function safeLink(value) {
  if(typeof value !== 'string' || value.length > 2048) return null;
  const raw=value.trim();
  if(/^#[A-Za-z][\w-]*$/.test(raw))return {href:raw,external:false};
  try {
    const u = new URL(raw);
    if (u.protocol !== 'https:' || u.username || u.password) return null;
    return {href:u.href,external:true};
  } catch {return null;}
}
function safeImage(value) {
  if(typeof value!=='string'||value.length>350)return null;
  const path=value.trim();
  // Only upload-created images from this project's own assets folder.
  if(!/^\.\/assets\/ads\/[a-zA-Z0-9_-]+\.(webp|jpe?g|png)$/.test(path))return null;
  return path;
}
function withinSchedule(item,at=Date.now()) {
  if(item.startAt && (!Number.isFinite(Date.parse(item.startAt)) || at < Date.parse(item.startAt)))return false;
  if(item.endAt && (!Number.isFinite(Date.parse(item.endAt)) || at >= Date.parse(item.endAt)))return false;
  return true;
}
function buildCard(entry,kind) {
  if(!entry || entry.enabled!==true || !withinSchedule(entry))return null;
  const target=safeLink(entry.url);
  if(!target || typeof entry.title!=='string'||!entry.title.trim()||entry.title.length>120)return null;
  if(kind==='banner'&&!safeImage(entry.image))return null;
  const a=document.createElement('a');
  a.className='ctad-card ctad-'+kind;
  a.href=target.href;
  if(target.external){a.target='_blank';a.rel='noopener noreferrer sponsored';a.referrerPolicy='strict-origin-when-cross-origin';}
  const promo=document.createElement('span');promo.className='ctad-label';promo.textContent='تبلیغات';
  const title=document.createElement('span');title.className='ctad-title';title.textContent=entry.title.trim();
  if(kind==='banner'){
    const img=document.createElement('img');img.className='ctad-img';img.loading='lazy';img.decoding='async';
    img.alt=(typeof entry.alt==='string'&&entry.alt.trim())?entry.alt.slice(0,160):entry.title.trim();
    img.src=safeImage(entry.image);
    // A broken image should never leave a half-empty ad in the UI.
    img.addEventListener('error',()=>{const host=a.closest('[data-ctad-slot]');a.remove();if(host&&!host.querySelector('.ctad-card')){host.hidden=true;host.closest('.ctad-table-row')?.setAttribute('hidden','');}});
    const meta=document.createElement('span');meta.className='ctad-meta';meta.append(promo,title);
    a.append(img,meta);
  }else{
    const symbol=document.createElement('span');symbol.className='ctad-link-icon';symbol.textContent='↗';symbol.setAttribute('aria-hidden','true');
    a.append(promo,title,symbol);
  }
  return a;
}
function renderSlots() {
  for (const host of $all('[data-ctad-slot]')) {
    const key=host.dataset.ctadSlot;
    if(!ALLOWED_SLOTS.has(key))continue;
    const setting=current?.placements?.[key];
    const signature=JSON.stringify([setting?.banner||null,setting?.link||null,
      Boolean(setting?.banner?.enabled&&withinSchedule(setting.banner)),
      Boolean(setting?.link?.enabled&&withinSchedule(setting.link))]);
    if(host.dataset.ctadSignature===signature)continue;
    const items=[buildCard(setting?.banner,'banner'),buildCard(setting?.link,'link')].filter(Boolean);
    host.replaceChildren(...items);
    host.dataset.ctadSignature=signature;
    host.hidden=!items.length;
    const row=host.closest('tr.ctad-table-row');
    if(row)row.hidden=!items.length;
  }
}
async function update({force=false}={}) {
  if(loading)return loading;
  if(!force && Date.now()-lastFetch<REFRESH_MS){renderSlots();return;}
  loading=(async()=>{
    try{
      const url='./data/ads.json?ctads='+Math.floor(Date.now()/REFRESH_MS);
      const response=await fetch(url,{cache:'no-store'});
      if(!response.ok)throw Error('ads HTTP '+response.status);
      const payload=await response.json();
      if(payload?.schema!==1||typeof payload.placements!=='object'||!payload.placements)throw Error('invalid ads schema');
      current=payload;
      lastFetch=Date.now();
      renderSlots();
    }catch(error){
      // Fail closed when the manifest is absent. If offline, keep the last valid manifest.
      if(!current){current={placements:{}};renderSlots();}
      console.warn('CurrencyTel ads: unavailable manifest',error);
    }finally{loading=null;}
  })();
  return loading;
}
window.addEventListener('ct:ads-slots-updated',renderSlots);
window.addEventListener('focus',()=>update());
document.addEventListener('visibilitychange',()=>{if(!document.hidden)update();});
window.addEventListener('online',()=>update({force:true}));
setInterval(()=>{if(!document.hidden)update();},REFRESH_MS);
update({force:true});
