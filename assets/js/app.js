import {getSnapshot,getHistory} from './data.js';
import {categories,categoryIcons,number,clean,safe,when,ageMinutes,changeText,parseLocalizedNumber} from './format.js';
import {drawHistory} from './chart.js';
import {PERIODS} from './history.js';
const el=id=>document.getElementById(id);
const state={items:[],history:[],filter:'all',query:'',sort:'default',favorites:new Set(),snapshot:null,loading:false,chartRange:'24h',slide:0,slidePaused:false};
const tehranDay=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tehran',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
function dailyChange(q){
  if(!q || state.snapshot?.market_day !== tehranDay())return null;
  const raw=q.day_change_pct;
  return raw===undefined||raw===null||raw===''||!Number.isFinite(Number(raw))?null:Number(raw);
}
function changeLabel(q){return changeText(dailyChange(q));}
function dailyAmount(q){
  if(!q || state.snapshot?.market_day!==tehranDay() || q.day_change===undefined || !Number.isFinite(Number(q.day_change)))return null;
  const amount=Number(q.day_change);
  return `${amount>0?'+':''}${number(amount,4)} ${q.unit}`;
}

try{state.favorites=new Set(JSON.parse(localStorage.getItem('ct-favorites')||'[]'));}catch{}

function status(kind,text){const e=el('status');e.className=`status ${kind}`;el('statusLabel').textContent=text;}
function toast(message){const div=el('toast');div.textContent=message;div.hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>div.hidden=true,3300);}
function addFavorites(id){
  if(state.favorites.has(id))state.favorites.delete(id);else state.favorites.add(id);
  try{localStorage.setItem('ct-favorites',JSON.stringify([...state.favorites]));}catch{}
  renderRows();el('favoriteCount').textContent=`★ علاقه‌مندی‌ها: ${number(state.favorites.size,0)}`;
}
function cards(){
  const ids=['usd','18ayar','bahar','btc','usdt','eur'];
  const meta={'usd':['دلار آمریکا','$'],'18ayar':['طلای ۱۸ عیار','✦'],'bahar':['سکه بهار آزادی','◉'],'btc':['بیت کوین','₿'],'usdt':['تتر','₮'],'eur':['یورو','€']};
  const available=ids.filter(id=>state.items.some(q=>q.id===id));
  const container=el('summaryGrid');
  container.innerHTML=available.map((id,index)=>{
    const q=state.items.find(x=>x.id===id),[title,icon]=meta[id];
    const [movement,kind]=changeLabel(q);
    return `<button type="button" class="summary-card" data-summary="${safe(id)}" data-slide="${index}" aria-label="جزئیات ${safe(title)}"><div class="summary-top"><span class="summary-kicker">${safe(title)}</span><span class="summary-icon">${icon}</span></div><div class="summary-number">${number(q.value)}</div><div class="summary-bottom"><span class="summary-unit">${safe(q.unit)}</span><span class="change ${kind}" dir="ltr">${movement}</span></div><div class="card-footnote">${safe(dailyAmount(q)??"مبنای تغییر امروز ثبت نشده")}</div></button>`;
  }).join('');
  state.slide=Math.min(state.slide,Math.max(0,available.length-1));
  el('carouselDots').innerHTML=available.map((_,i)=>`<button type="button" data-carousel-dot="${i}" aria-label="نمایش قیمت ${safe(meta[available[i]][0])}" aria-pressed="${i===state.slide}"></button>`).join('');
  selectSlide(state.slide,false);
}
function selectSlide(index,animate=true){
  const container=el('summaryGrid');
  const cards=[...container.querySelectorAll('[data-slide]')];
  if(!cards.length)return;
  state.slide=(index+cards.length)%cards.length;
  const slideRight=cards[state.slide].getBoundingClientRect().right;
  const viewRight=container.getBoundingClientRect().right;
  const left=container.scrollLeft + (slideRight-viewRight);
  container.scrollTo({left,behavior:animate?'smooth':'instant'});
  el('carouselDots').querySelectorAll('button').forEach((dot,i)=>{dot.classList.toggle('active',i===state.slide);dot.setAttribute('aria-pressed',String(i===state.slide));});
}
function marketPulse(){
  const eligible=state.items.filter(q=>dailyChange(q)!==null);
  el('pulseAssets').textContent=number(state.items.length,0);
  el('pulseUp').textContent=number(eligible.filter(q=>dailyChange(q)>0).length,0);
  el('pulseDown').textContent=number(eligible.filter(q=>dailyChange(q)<0).length,0);
  el('pulseMarkets').textContent=number(new Set(state.items.map(q=>q.category)).size,0);
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
  if(state.sort==='change_desc')items.sort((a,b)=>Number(dailyChange(b)??-999)-Number(dailyChange(a)??-999));
  return items;
}
function renderRows(){
  const data=filteredItems();
  el('countLabel').textContent=`${number(data.length,0)} مورد از ${number(state.items.length,0)} قیمت ثبت‌شده`;
  el('marketCoverage').textContent=`${number(state.snapshot?.social_count||0,0)} نرخ اصلی • ${number(state.snapshot?.extra_count||0,0)} بازار تکمیلی`;
  const tbody=el('priceRows');
  if(!data.length){tbody.innerHTML='<tr><td class="blank-state" colspan="4">موردی پیدا نشد. فیلتر یا عبارت جستجو را تغییر دهید.</td></tr>';return;}
  tbody.innerHTML=data.map(q=>{
    const [text,kind]=changeLabel(q);
    return `<tr data-detail="${safe(q.id)}" tabindex="0" aria-label="جزئیات ${safe(q.label)}"><td><div class="asset-title"><span class="asset-symbol">${safe(categoryIcons[q.category]||'◌')}</span><div>${safe(q.label)}<span class="asset-meta">${safe(q.id.toUpperCase())} · ${safe(categories[q.category]||'سایر')}</span></div></div></td><td><span class="money-number">${number(q.value)}</span><span class="money-unit">${safe(q.unit)}</span></td><td><span class="change ${kind}">${text}</span></td><td><button class="favorite-btn ${state.favorites.has(q.id)?'saved':''}" type="button" data-favorite="${safe(q.id)}" aria-pressed="${state.favorites.has(q.id)}" aria-label="${safe(q.label)}: علاقه‌مندی">${state.favorites.has(q.id)?'★':'☆'}</button></td></tr>`;
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
  const model=drawHistory(el('historyChart'),state.history,id,{
    range:state.chartRange,emptyEl:el('chartEmpty'),tooltipEl:el('chartTooltip')
  });
  const value=model.last?.value ?? item?.value;
  el('chartNumber').textContent=item&&Number.isFinite(Number(value))?`${number(value)} ${item.unit}`:'—';
  const diff=model.difference;
  const trend=el('chartTrend');
  trend.className=`chart-trend ${diff===null?'flat':diff>0?'up':diff<0?'down':'flat'}`;
  trend.textContent=diff===null?'تغییر نامشخص':`${model.percent>0?'+':''}${number(model.percent,2)}٪`;
  el('chartDelta').textContent=diff===null?'—':`${diff>0?'+':''}${number(diff,4)} ${item?.unit||''}`;
  el('chartCount').textContent=number(model.entries.length,0);
  const label=PERIODS[state.chartRange]?.label||'۲۴ ساعت';
  const first=model.first,last=model.last;
  el('chartMeta').textContent=!first ? `در ${label} گذشته برای این دارایی داده‌ای ثبت نشده؛ بازه دیگری را انتخاب کنید.`
    : model.entries.length===1 ? `تنها یک مشاهده در ${label} اخیر ثبت شده؛ برای محاسبه تغییر به دو مشاهده نیاز است. آخرین ثبت: ${when(last.t)}`
    : `پوشش واقعی ${when(first.t)} تا ${when(last.t)} • تغییر صرفاً بین اولین و آخرین نمونه همین فاصله محاسبه شده است.`;
}
function renderConverter(){
  const item=state.items.find(q=>q.id===el('converterAsset').value);
  const amount=parseLocalizedNumber(el('converterAmount').value);
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
  const now=new Date();
  const clock=new Intl.DateTimeFormat('fa-IR',{timeZone:'Asia/Tehran',hour:'2-digit',minute:'2-digit',hour12:false}).format(now);
  const date=new Intl.DateTimeFormat('fa-IR',{timeZone:'Asia/Tehran',weekday:'long',year:'numeric',month:'long',day:'numeric'}).format(now);
  el('ageLabel').textContent=clock;
  el('currentDate').textContent=date;
  const snapshot=state.snapshot;
  const actual=when(snapshot?.fetched_at);
  el('updatedAt').textContent=snapshot?.bootstrap?'نمونه آرشیوی':actual;
  el('footerTime').textContent=actual;
  const age=ageMinutes(snapshot?.fetched_at);
  if(snapshot?.bootstrap||!Number.isFinite(age)) status('stale','داده آزمایشی');
  else if(age<=90)status('ok','آخرین داده ثبت‌شده');
  else status('stale','داده قدیمی');
}
function renderAll(){cards();marketPulse();renderRows();selectOptions();renderChart();renderConverter();renderTime();el('favoriteCount').textContent=`★ علاقه‌مندی‌ها: ${number(state.favorites.size,0)}`;}
async function refresh({showToast=false}={}){
  if(state.loading)return;
  state.loading=true;
  el('errorMessage').hidden=true;
  try{
    const [snapshot,history]=await Promise.all([getSnapshot(),getHistory()]);
    if(!snapshot.items.length)throw new Error('هنوز داده‌ای ثبت نشده؛ ابتدا اجرای GitHub Actions باید موفق شود.');
    state.items=snapshot.items;state.history=history;state.snapshot=snapshot;state.renderedDay=tehranDay();renderAll();
    if(showToast)toast('داده‌های ثبت‌شده بررسی شدند.');
  }catch(error){
    const message=error instanceof Error?error.message:'خطا در دریافت داده';
    el('errorMessage').textContent=message;el('errorMessage').hidden=false;
    if(!state.items.length){el('priceRows').innerHTML='<tr><td colspan="4" class="blank-state">امکان بارگیری نرخ‌ها وجود ندارد. اتصال اینترنت و اجرای پروژه را بررسی کنید.</td></tr>';status('error','عدم دسترسی به اطلاعات');}
    else{status('stale','نمایش آخرین داده در دسترس');toast('بارگیری تازه موفق نبود؛ داده قبلی نمایش داده می‌شود.');}
  }finally{state.loading=false;}
}
const detailMetric=(label,value)=>`<div class="detail-stat"><small>${safe(label)}</small><b>${safe(value)}</b></div>`;
function openDetail(id){
  const q=state.items.find(x=>x.id===id);if(!q)return;
  const [change,kind]=changeLabel(q);
  const metrics=[];
  metrics.push(detailMetric('تغییر از شروع روز',change));
  if(dailyAmount(q)!==null)metrics.push(detailMetric('مقدار تغییر امروز',dailyAmount(q)));
  if(q.day_open!==undefined && state.snapshot?.market_day===tehranDay()){metrics.push(detailMetric('اولین نرخ ثبت‌شده امروز',`${number(q.day_open)} ${q.unit}`));metrics.push(detailMetric('زمان مبنا',when(q.day_open_at)));}
  if(q.buy!==undefined)metrics.push(detailMetric('نرخ خرید',`${number(q.buy)} ${q.unit}`));
  if(q.usd_value!==undefined)metrics.push(detailMetric('قیمت دلاری',`${number(q.usd_value)} دلار`));
  if(q.toman_value!==undefined)metrics.push(detailMetric('قیمت تومانی',`${number(q.toman_value)} تومان`));
  if(q.bubble_pct!==undefined)metrics.push(detailMetric('حباب',`${number(q.bubble_pct,2)}٪`));
  if(q.market_status)metrics.push(detailMetric('وضعیت بازار',String(q.market_status)));
  el('detailContent').innerHTML=`<div class="eyebrow">${safe(categories[q.category]||'بازار')}</div><h2 id="detailTitle">${safe(q.label)}</h2><div class="detail-intro">${safe(q.id.toUpperCase())} · آخرین نرخ ثبت‌شده</div><div class="detail-price">${number(q.value)}</div><div class="detail-unit">${safe(q.unit)} <span class="change ${kind}" dir="ltr">${change}</span></div><div class="detail-grid">${metrics.join('')}</div><div class="detail-spark-panel"><div class="detail-spark-heading"><strong>روند ثبت‌شده ۷ روز اخیر</strong><button id="detailFullChart" type="button" class="detail-chart-link" data-full-chart="${safe(q.id)}">تحلیل کامل ←</button></div><div class="detail-spark-wrap"><svg id="detailHistoryChart" role="img" aria-label="روند ۷ روز اخیر"></svg><div id="detailChartEmpty" class="mini-empty" hidden>هنوز داده کافی ثبت نشده</div></div></div><p class="detail-note">زمان دریافت: ${safe(when(q.received_at||state.snapshot?.fetched_at))}. اطلاعات صرفاً جهت اطلاع‌رسانی است.</p>`;
  el('detailBackdrop').hidden=false;el('detailSheet').hidden=false;
  document.body.style.overflow='hidden';
  drawHistory(el('detailHistoryChart'),state.history,id,{range:'7d',compact:true,emptyEl:el('detailChartEmpty')});
  el('detailClose').focus();
}
function closeDetail(){el('detailBackdrop').hidden=true;el('detailSheet').hidden=true;document.body.style.overflow='';}
function setupNavigation(){
  const links=[...document.querySelectorAll('[data-nav]')];
  const active=key=>links.forEach(a=>a.classList.toggle('active',a.dataset.nav===key));
  links.forEach(a=>a.addEventListener('click',()=>active(a.dataset.nav)));
  if('IntersectionObserver' in window){
    const observer=new IntersectionObserver(entries=>{
      const entry=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];
      if(entry)active(entry.target.id);
    },{rootMargin:'-18% 0px -62% 0px',threshold:0});
    ['home','prices','tools','connect'].forEach(id=>{const target=el(id);if(target)observer.observe(target);});
  }
}
function events(){
  el('summaryGrid').addEventListener('click',e=>{const card=e.target.closest('[data-summary]');if(card)openDetail(card.dataset.summary);});
  el('searchInput').addEventListener('input',e=>{state.query=clean(e.target.value);renderRows();});
  el('filterBar').addEventListener('click',e=>{
    const button=e.target.closest('[data-filter]');if(!button)return;
    state.filter=button.dataset.filter;
    for(const b of el('filterBar').querySelectorAll('button')){b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));}
    renderRows();
  });
  el('sortInput').addEventListener('change',e=>{state.sort=e.target.value;renderRows();});
  el('priceRows').addEventListener('click',e=>{const btn=e.target.closest('[data-favorite]');if(btn){addFavorites(btn.dataset.favorite);return;}const row=e.target.closest('[data-detail]');if(row)openDetail(row.dataset.detail);});
  el('priceRows').addEventListener('keydown',e=>{const row=e.target.closest('[data-detail]');if(row&&(e.key==='Enter'||e.key===' ')){e.preventDefault();openDetail(row.dataset.detail);}});
  el('detailClose').addEventListener('click',closeDetail);
  el('detailBackdrop').addEventListener('click',closeDetail);
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!el('detailSheet').hidden)closeDetail();});
  setupNavigation();
  el('chartAsset').addEventListener('change',renderChart);
  el('chartRanges').addEventListener('click',event=>{
    const button=event.target.closest('[data-range]');
    if(!button||!PERIODS[button.dataset.range])return;
    state.chartRange=button.dataset.range;
    el('chartRanges').querySelectorAll('[data-range]').forEach(b=>{
      const chosen=b===button;b.classList.toggle('active',chosen);b.setAttribute('aria-pressed',String(chosen));
    });
    renderChart();
  });
  el('detailContent').addEventListener('click',event=>{
    const btn=event.target.closest('[data-full-chart]');if(!btn)return;
    closeDetail();
    el('chartAsset').value=btn.dataset.fullChart;
    state.chartRange='7d';
    el('chartRanges').querySelectorAll('[data-range]').forEach(b=>{
      const chosen=b.dataset.range==='7d';b.classList.toggle('active',chosen);b.setAttribute('aria-pressed',String(chosen));
    });
    renderChart();el('tools').scrollIntoView({behavior:'smooth',block:'start'});
  });
  if('ResizeObserver' in window){
    const ro=new ResizeObserver(()=>{if(state.snapshot)renderChart();});
    ro.observe(el('chartPlot'));
  }
  el('converterAsset').addEventListener('change',renderConverter);
  el('converterAmount').addEventListener('input',renderConverter);
  const theme=()=>{document.body.classList.toggle('light');try{localStorage.setItem('ct-theme',document.body.classList.contains('light')?'light':'dark');}catch{}};
  el('themeBtn').addEventListener('click',theme);
  try{if(localStorage.getItem('ct-theme')==='light')document.body.classList.add('light');}catch{}
  const carousel=el('summaryGrid');
  carousel.addEventListener('mouseenter',()=>{state.slidePaused=true;});
  carousel.addEventListener('mouseleave',()=>{state.slidePaused=false;});
  carousel.addEventListener('focusin',()=>{state.slidePaused=true;});
  carousel.addEventListener('focusout',e=>{if(!carousel.contains(e.relatedTarget))state.slidePaused=false;});
  carousel.addEventListener('touchstart',()=>{state.slidePaused=true;},{passive:true});
  carousel.addEventListener('touchend',()=>{setTimeout(()=>{state.slidePaused=false;},5000);},{passive:true});
  el('carouselPrev').addEventListener('click',()=>selectSlide(state.slide-1));
  el('carouselNext').addEventListener('click',()=>selectSlide(state.slide+1));
  el('carouselDots').addEventListener('click',e=>{const dot=e.target.closest('[data-carousel-dot]');if(dot)selectSlide(Number(dot.dataset.carouselDot));});
  carousel.addEventListener('scroll',()=>{
    clearTimeout(carousel._scrollTimer);
    carousel._scrollTimer=setTimeout(()=>{
      const cards=[...carousel.querySelectorAll('[data-slide]')];
      if(!cards.length)return;
      const x=carousel.getBoundingClientRect().right;
      const closest=cards.reduce((best,card,i)=>Math.abs(card.getBoundingClientRect().right-x)<best.dist?{i,dist:Math.abs(card.getBoundingClientRect().right-x)}:best,{i:0,dist:Infinity});
      state.slide=closest.i;
      el('carouselDots').querySelectorAll('button').forEach((dot,i)=>{dot.classList.toggle('active',i===state.slide);dot.setAttribute('aria-pressed',String(i===state.slide));});
    },180);
  },{passive:true});
  window.addEventListener('online',()=>refresh());
  window.addEventListener('visibilitychange',()=>{if(!document.hidden&&state.snapshot)renderTime();});
}
function init(){
  events();refresh();
  setInterval(()=>{if(!document.hidden)refresh();},15*60*1000);
  setInterval(()=>{if(!document.hidden){
    renderTime();
    const today=tehranDay();
    if(state.renderedDay!==today){state.renderedDay=today;if(state.items.length){cards();marketPulse();renderRows();}}
  }},30000);
  if(!matchMedia('(prefers-reduced-motion: reduce)').matches){
    setInterval(()=>{if(!document.hidden&&!state.slidePaused&&state.items.length)selectSlide(state.slide+1);},6500);
  }
  if('serviceWorker'in navigator&&location.protocol==='https:')navigator.serviceWorker.register('./sw.js').catch(()=>{});
}
init();
