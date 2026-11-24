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
function buildCard(entry) {
  if(!entry || entry.enabled!==true || !withinSchedule(entry))return null;
  const target=safeLink(entry.url),picture=safeImage(entry.image);
  if(!target||!picture)return null;
  const a=document.createElement('a');
  a.className='ctad-card ctad-banner';a.href=target.href;
  const name=typeof entry.title==='string'&&entry.title.trim()?entry.title.trim():'بنر تبلیغاتی';
  a.setAttribute('aria-label','تبلیغات: '+name);
  if(target.external){a.target='_blank';a.rel='noopener noreferrer sponsored';a.referrerPolicy='strict-origin-when-cross-origin';}
  const img=document.createElement('img');img.className='ctad-img';img.loading='lazy';img.decoding='async';
  img.alt=(typeof entry.alt==='string'&&entry.alt.trim())?entry.alt.slice(0,160):name;
  img.src=picture;
  img.addEventListener('error',()=>{
    const host=a.closest('[data-ctad-slot]');a.remove();
    if(host&&!host.querySelector('.ctad-card')){
      host.hidden=true;host.closest('.ctad-table-row')?.setAttribute('hidden','');
    }
  });
  const badge=document.createElement('span');badge.className='ctad-label';badge.textContent='تبلیغات';
  a.append(img,badge);return a;
}
function renderSlots() {
  for (const host of $all('[data-ctad-slot]')) {
    const key=host.dataset.ctadSlot;
    if(!ALLOWED_SLOTS.has(key))continue;
    const setting=current?.placements?.[key];
    const signature=JSON.stringify([setting?.banner||null,Boolean(setting?.banner?.enabled&&withinSchedule(setting.banner))]);
    if(host.dataset.ctadSignature===signature)continue;
    const items=[buildCard(setting?.banner)].filter(Boolean);
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
