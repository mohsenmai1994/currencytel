/** CurrencyTel Ads: public display only; credentials never enter this module. */
const ALLOWED_SLOTS = new Set([
  'home_quick','market_between','market_inline','news_inline',
  'world_footer','gold_footer','tools_footer'
]);
const APP_ROOT = new URL('../../', import.meta.url);
const ADS_ROOT = new URL('assets/ads/', APP_ROOT);
const REFRESH_MS = 5 * 60 * 1000;
const failedImages = new Map();
let manifest = null, loading = null, lastFetch = 0;

function safeLink(value) {
  if (typeof value !== 'string' || value.length > 2048) return null;
  const raw = value.trim();
  if (/^#[A-Za-z][\w-]*$/.test(raw)) return {href:raw,external:false};
  try {
    const url = new URL(raw);
    if (url.protocol !== 'https:' || url.username || url.password) return null;
    return {href:url.href,external:true};
  } catch { return null; }
}

/** Resolve existing upload paths against the app root, not the current page URL.
 *  Supports ./assets/ads/..., assets/ads/..., /assets/ads/... and
 *  the same-origin absolute URLs from earlier versions. */
function safeImage(value) {
  if (typeof value !== 'string' || value.length > 2048) return null;
  let raw = value.trim();
  if (/^\/assets\/ads\//.test(raw)) raw = '.' + raw;
  try {
    const url = new URL(raw, APP_ROOT);
    if (url.origin !== ADS_ROOT.origin || !url.pathname.startsWith(ADS_ROOT.pathname)) return null;
    const filename = url.pathname.slice(ADS_ROOT.pathname.length);
    if (!/^[A-Za-z0-9_-]+\.(?:webp|jpe?g|png)$/i.test(filename)) return null;
    // Strip stale query/hash components and use a fixed, app-relative base.
    return new URL('assets/ads/' + filename, APP_ROOT).href;
  } catch { return null; }
}

function isScheduled(entry, at = Date.now()) {
  if (entry.startAt && (!Number.isFinite(Date.parse(entry.startAt)) || at < Date.parse(entry.startAt))) return false;
  if (entry.endAt && (!Number.isFinite(Date.parse(entry.endAt)) || at >= Date.parse(entry.endAt))) return false;
  return true;
}
function showHost(host,visible){
  host.hidden = !visible;
  const tr = host.closest('tr.ctad-table-row');
  if (tr) tr.hidden = !visible;
}
function buildCard(slot, entry, host, photo) {
  const target = safeLink(entry.url);
  if (!target || !photo) return null;
  const anchor = document.createElement('a');
  anchor.className = 'ctad-card ctad-banner';
  anchor.href = target.href;
  const title = typeof entry.title === 'string' && entry.title.trim() ? entry.title.trim() : 'بنر تبلیغاتی';
  anchor.setAttribute('aria-label','تبلیغات: '+title);
  if (target.external) {
    anchor.target = '_blank'; anchor.rel = 'noopener noreferrer sponsored';
    anchor.referrerPolicy = 'strict-origin-when-cross-origin';
  }
  const image = document.createElement('img');
  image.className = 'ctad-img'; image.loading = 'lazy'; image.decoding = 'async';
  image.alt = typeof entry.alt === 'string' && entry.alt.trim() ? entry.alt.slice(0,160) : title;
  const failureKey = slot + '|' + photo;
  image.addEventListener('load',()=>{
    failedImages.delete(failureKey);
    if (host.contains(anchor)) showHost(host,true);
  });
  image.addEventListener('error',()=>{
    if (!host.contains(anchor)) return;
    // GitHub Pages may deploy ads.json before the newly uploaded image.
    // Hide the broken frame, retain the manifest and retry with backoff.
    const previous = failedImages.get(failureKey)?.attempts || 0;
    const attempts = previous + 1;
    const delay = Math.min(10_000 * 2 ** Math.min(attempts-1,5), REFRESH_MS);
    failedImages.set(failureKey,{attempts,until:Date.now()+delay});
    host.replaceChildren(); host.removeAttribute('data-ctad-signature');
    showHost(host,false);
    window.setTimeout(renderSlots,delay+50);
    console.warn('CurrencyTel ad image: retry scheduled',slot,photo);
  });
  const caption = document.createElement('span');caption.className = 'ctad-label';caption.textContent = 'تبلیغات';
  anchor.append(image,caption);
  const previous = failedImages.get(failureKey);
  image.src = previous?.attempts ? photo + '?ctad_retry=' + previous.attempts + '-' + Math.floor(Date.now()/10_000) : photo;
  return anchor;
}
function renderSlots() {
  for (const host of document.querySelectorAll('[data-ctad-slot]')) {
    const slot = host.dataset.ctadSlot;
    if (!ALLOWED_SLOTS.has(slot) || host.closest('#connect')) {
      host.replaceChildren();showHost(host,false);continue;
    }
    if (slot === 'market_between' &&
        !document.getElementById('marketFeaturePanel')?.hidden) {
      // Avoid two advertising cards directly beneath one another while a tool is open.
      host.replaceChildren();host.removeAttribute('data-ctad-signature');showHost(host,false);continue;
    }
    if (slot === 'tools_footer' &&
        !['chart','converter'].includes(host.closest('#marketFeaturePanel')?.dataset.activeTool)) {
      host.replaceChildren();host.removeAttribute('data-ctad-signature');showHost(host,false);continue;
    }
    const entry = manifest?.placements?.[slot]?.banner;
    const picture = safeImage(entry?.image);
    const valid = entry?.enabled === true && isScheduled(entry) && !!picture && !!safeLink(entry.url);
    const signature = JSON.stringify(valid ? entry : null);
    if (host.dataset.ctadSignature === signature && host.querySelector('.ctad-card')) continue;
    if (!valid) {
      host.replaceChildren();host.dataset.ctadSignature=signature;showHost(host,false);continue;
    }
    const failure = failedImages.get(slot+'|'+picture);
    if (failure?.until > Date.now()) {host.replaceChildren();host.removeAttribute('data-ctad-signature');showHost(host,false);continue;}
    const card = buildCard(slot,entry,host,picture);
    if (!card) {host.replaceChildren();showHost(host,false);continue;}
    host.replaceChildren(card);host.dataset.ctadSignature=signature;
    showHost(host,true);
  }
}
async function update({force=false}={}) {
  if (loading) return loading;
  if (!force && Date.now()-lastFetch < REFRESH_MS) {renderSlots();return;}
  loading=(async()=>{
    try {
      // Resolve relative to assets/js/ads.js so routes inside the PWA cannot break ads.
      const url = new URL('data/ads.json',APP_ROOT);
      url.searchParams.set('ctads',String(Math.floor(Date.now()/REFRESH_MS)));
      const result = await fetch(url,{cache:'no-store'});
      if (!result.ok) throw new Error('HTTP '+result.status);
      const data = await result.json();
      if (data?.schema!==1 || !data.placements || typeof data.placements!=='object') throw Error('invalid ads manifest');
      manifest = data;lastFetch=Date.now();renderSlots();
    } catch(error) {
      // Never replace the last known good ads on temporary network problems.
      if (!manifest) {manifest={placements:{}};renderSlots();}
      console.warn('CurrencyTel ads: could not refresh settings',error);
    } finally {loading=null;}
  })();
  return loading;
}
window.addEventListener('ct:ads-slots-updated',renderSlots);
window.addEventListener('focus',()=>update());
document.addEventListener('visibilitychange',()=>{if (!document.hidden) update({force:true});});
window.addEventListener('online',()=>update({force:true}));
window.setInterval(()=>{if(!document.hidden) update({force:true});},REFRESH_MS);
update({force:true});
