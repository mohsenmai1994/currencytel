const APP_CACHE = 'currencytel-shell-v2';
const DATA_CACHE = 'currencytel-data-v2';
const shell = ['./','./index.html','./assets/css/main.css','./assets/js/app.js','./assets/js/data.js','./assets/js/format.js','./assets/js/chart.js','./assets/icons/icon.svg','./manifest.webmanifest'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(APP_CACHE).then(cache=>cache.addAll(shell)));self.skipWaiting();});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>![APP_CACHE,DATA_CACHE].includes(k)).map(k=>caches.delete(k)))));self.clients.claim();});
self.addEventListener('fetch',event=>{
  const request=event.request;
  if(request.method!=='GET'||new URL(request.url).origin!==self.location.origin)return;
  const url=new URL(request.url);
  if(url.pathname.endsWith('/data/market.json')||url.pathname.endsWith('/data/history.json')){
    event.respondWith(fetch(request).then(response=>{if(response.ok){const clone=response.clone();caches.open(DATA_CACHE).then(cache=>cache.put(request,clone));}return response;}).catch(()=>caches.match(request)));
  }else{event.respondWith(caches.match(request).then(cached=>cached||fetch(request).then(response=>{if(response.ok)caches.open(APP_CACHE).then(cache=>cache.put(request,response.clone()));return response;})));}
});
