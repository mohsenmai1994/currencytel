import {getSnapshot,getHistory} from './data.js';
import {categories,categoryIcons,number,clean,safe,when,ageMinutes,changeText} from './format.js';
import {drawHistory} from './chart.js';
const el=id=>document.getElementById(id);
const state={items:[],history:[],filter:'all',query:'',sort:'default',favorites:new Set(),snapshot:null,loading:false};
try{state.favorites=new Set(JSON.parse(localStorage.getItem('ct-favorites')||'[]'));}catch{}

function status(kind,text){const e=el('status');e.className=`status ${kind}`;el('statusLabel').textContent=text;}
function toast(message){const div=el('toast');div.textContent=message;div.hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>div.hidden=true,3300);}
function addFavorites(id){
  if(state.favorites.has(id))state.favorites.delete(id);else state.favorites.add(id);
  try{localStorage.setItem('ct-favorites',JSON.stringify([...state.favorites]));}catch{}
  renderRows();el('favoriteCount').textContent=`★ علاقه‌مندی‌ها: ${state.favorites.size.toLocaleString('fa-IR')}`;
}
function cards(){
  const ids=['usd','18ayar','bahar','btc'];
  const meta={'usd':['دلار آمریکا','$'],'18ayar':['طلای ۱۸ عیار','✦'],'bahar':['سکه بهار آزادی','◉'],'btc':['بیت کوین','₿']};
  el('summaryGrid').innerHTML=ids.map(id=>{
    const q=state.items.find(x=>x.id===id), [title,icon]=meta[id];
    return `<div class="summary-card"><div class="summary-top"><span class="summary-kicker">${safe(title)}</span><span class="summary-icon">${icon}</span></div><div class="summary-number">${q?number(q.value):'—'}</div><div class="summary-unit">${q?safe(q.unit):'در انتظار داده'}</div></div>`;
  }).join('');
}
function filteredItems(){
  let items=state.items.filter(item=>{
    if(state.filter==='favorite' && !state.favorites.has(item.id))return false;
    if(state.filter!=='all' && state.filter!=='favorite' && item.category!==state.filter)return false;
    if(state.query && !clean(item.label+' '+item.id+' '+item.category).includes(state.query))return false;
    return true;
  });
  if(state.sort==='name')items.sort((a,b)=>a.label.localeCompare(b.label,'fa'));
  if(state.sort==='price_desc')items.sort((a,b)=>Number(b.value)-Number(a.value));
  if(state.sort==='change_desc')items.sort((a,b)=>Number(b.change_pct??-999)-Number(a.change_pct??-999));
  return items;
}
function renderRows(){
  const data=filteredItems();
  el('countLabel').textContent=`${data.length.toLocaleString('fa-IR')} مورد از ${state.items.length.toLocaleString('fa-IR')} قیمت ثبت‌شده`;
  el('marketCoverage').textContent=`${(state.snapshot?.social_count||0).toLocaleString('fa-IR')} نرخ اصلی • ${(state.snapshot?.extra_count||0).toLocaleString('fa-IR')} بازار تکمیلی`;
  const tbody=el('priceRows');
  if(!data.length){tbody.innerHTML='<tr><td class="blank-state" colspan="5">موردی پیدا نشد. فیلتر یا عبارت جستجو را تغییر دهید.</td></tr>';return;}
  tbody.innerHTML=data.map(q=>{
    const [text,kind]=changeText(q.change_pct);
    const hi=q.day_high===undefined?'—':number(q.day_high);
    const lo=q.day_low===undefined?'—':number(q.day_low);
    return `<tr><td><div class="asset-title"><span class="asset-symbol">${safe(categoryIcons[q.category]||'◌')}</span><div>${safe(q.label)}<span class="asset-source">${safe(q.id.toUpperCase())} · ${safe(categories[q.category]||'سایر')}</span></div></div></td><td><span class="money-number">${number(q.value)}</span><span class="money-unit">${safe(q.unit)}</span></td><td><span class="change ${kind}">${text}</span></td><td><span class="day-range">${lo} / ${hi}</span></td><td><button class="favorite-btn ${state.favorites.has(q.id)?'saved':''}" type="button" data-favorite="${safe(q.id)}" aria-pressed="${state.favorites.has(q.id)}" aria-label="${safe(q.label)}: علاقه‌مندی">${state.favorites.has(q.id)?'★':'☆'}</button></td></tr>`;
  }).join('');
}
function selectOptions(){
  const chartSelect=el('chartAsset'),converterSelect=el('converterAsset');
  const lastChart=chartSelect.value||'usd',lastConv=converterSelect.value||'usd';
  // The 14 broadcast assets remain first; extras follow, in source order.
  const options=state.items.map(q=>`<option value="${safe(q.id)}">${safe(q.label)} (${safe(q.unit)})</option>`).join('');
  chartSelect.innerHTML=options;
  converterSelect.innerHTML=state.items.filter(q=>q.unit==='تومان'||/^(دلار|پوند|یورو|یوان)(\/|$)/.test(q.unit)).map(q=>`<option value=\"${safe(q.id)}\">${safe(q.label)} (${safe(q.unit)})</option>`).join('');
  chartSelect.value=state.items.some(q=>q.id===lastChart)?lastChart:'usd';
  converterSelect.value=state.items.some(q=>q.id===lastConv)?lastConv:'usd';
}
function renderChart(){
  const id=el('chartAsset').value;
  const item=state.items.find(x=>x.id===id);
  el('chartNumber').textContent=item?`${number(item.value)} ${item.unit}`:'—';
  el('chartMeta').textContent='در حال بررسی تاریخچه';
  drawHistory(el('historyChart'),state.history,id);
}
function renderConverter(){
  const item=state.items.find(q=>q.id===el('converterAsset').value);
  const amount=Number(el('converterAmount').value);
  const dollar=state.items.find(q=>q.id==='usd');
  if(!item||!Number.isFinite(amount)||amount<0){el('conversionValue').textContent='—';return;}
  let toman=Number(item.value)*amount;
  const foreign={'دلار':'usd','پوند':'gbp','یورو':'eur','یوان':'cny'};
  const base=Object.keys(foreign).find(word=>item.unit.startsWith(word));
  if(base){
    const exchange=state.items.find(q=>q.id===foreign[base]);
    if(!exchange){el('conversionValue').textContent='نرخ تبدیل موجود نیست';return;}
    toman*=Number(exchange.value);
  }
  el('conversionValue').textContent=`${number(toman,2)} تومان`;
  el('conversionNote').textContent=`${number(amount,4)} × ${number(item.value)} ${item.unit}؛${base?' تبدیل با نرخ ارز آزاد؛':''} بدون کارمزد یا هزینه معامله`;
}
function renderTime(){
  const snapshot=state.snapshot;
  el('updatedAt').textContent=when(snapshot?.fetched_at);
  el('footerTime').textContent=when(snapshot?.fetched_at);
  const age=ageMinutes(snapshot?.fetched_at);
  if(snapshot?.bootstrap || !Number.isFinite(age)){
    status('stale','آخرین گزارش آرشیوی');el('ageLabel').textContent='نمونه برگرفته از گزارش قبلی؛ زمان آخرین به‌روزرسانی مشخص نیست';return;
  }
  el('ageLabel').textContent=age<1?'همین حالا دریافت شده':`${age.toLocaleString('fa-IR')} دقیقه از آخرین دریافت گذشته است`;
  if(age<=90)status('ok','داده دریافت‌شده');else status('stale','ممکن است داده‌ها قدیمی باشند');
}
function renderAll(){cards();renderRows();selectOptions();renderChart();renderConverter();renderTime();el('favoriteCount').textContent=`★ علاقه‌مندی‌ها: ${state.favorites.size.toLocaleString('fa-IR')}`;}
async function refresh({showToast=false}={}){
  if(state.loading)return;
  state.loading=true;el('refreshBtn').disabled=true;
  el('errorMessage').hidden=true;
  try{
    const [snapshot,history]=await Promise.all([getSnapshot(),getHistory()]);
    if(!snapshot.items.length)throw new Error('هنوز داده‌ای ثبت نشده؛ ابتدا اجرای GitHub Actions باید موفق شود.');
    state.items=snapshot.items;state.history=history;state.snapshot=snapshot;renderAll();
    if(showToast)toast('داده‌های ثبت‌شده بررسی شدند.');
  }catch(error){
    const message=error instanceof Error?error.message:'خطا در دریافت داده';
    el('errorMessage').textContent=message;el('errorMessage').hidden=false;
    if(!state.items.length){el('priceRows').innerHTML='<tr><td colspan="5" class="blank-state">امکان بارگیری نرخ‌ها وجود ندارد. اتصال اینترنت و اجرای پروژه را بررسی کنید.</td></tr>';status('error','عدم دسترسی به اطلاعات');}
    else{status('stale','نمایش آخرین داده در دسترس');toast('بارگیری تازه موفق نبود؛ داده قبلی نمایش داده می‌شود.');}
  }finally{state.loading=false;el('refreshBtn').disabled=false;}
}
function events(){
  el('searchInput').addEventListener('input',e=>{state.query=clean(e.target.value);renderRows();});
  el('filterBar').addEventListener('click',e=>{
    const button=e.target.closest('[data-filter]');if(!button)return;
    state.filter=button.dataset.filter;
    for(const b of el('filterBar').querySelectorAll('button')){b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));}
    renderRows();
  });
  el('sortInput').addEventListener('change',e=>{state.sort=e.target.value;renderRows();});
  el('priceRows').addEventListener('click',e=>{const btn=e.target.closest('[data-favorite]');if(btn)addFavorites(btn.dataset.favorite);});
  el('chartAsset').addEventListener('change',renderChart);
  el('converterAsset').addEventListener('change',renderConverter);
  el('converterAmount').addEventListener('input',renderConverter);
  el('refreshBtn').addEventListener('click',()=>refresh({showToast:true}));
  const theme=()=>{document.body.classList.toggle('light');try{localStorage.setItem('ct-theme',document.body.classList.contains('light')?'light':'dark');}catch{}};
  el('themeBtn').addEventListener('click',theme);
  try{if(localStorage.getItem('ct-theme')==='light')document.body.classList.add('light');}catch{}
  let installPrompt=null;
  window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;el('installBtn').hidden=false;});
  el('installBtn').addEventListener('click',async()=>{if(!installPrompt)return;installPrompt.prompt();try{await installPrompt.userChoice;}catch{}installPrompt=null;el('installBtn').hidden=true;});
  window.addEventListener('appinstalled',()=>{el('installBtn').hidden=true;toast('CurrencyTel نصب شد.');});
  window.addEventListener('online',()=>refresh());
  window.addEventListener('visibilitychange',()=>{if(!document.hidden&&state.snapshot)renderTime();});
}
function init(){events();refresh();setInterval(()=>{if(!document.hidden)refresh();},15*60*1000);if('serviceWorker'in navigator&&location.protocol==='https:')navigator.serviceWorker.register('./sw.js').catch(()=>{});}
init();
