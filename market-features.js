/** CurrencyTel market tools — independently mounted, keeps legacy chart/converter DOM intact. */
export function initMarketFeatures({getGoldQuote}={}) {
  const cards=document.getElementById('marketFeatureCards'),panel=document.getElementById('marketFeaturePanel');
  const title=document.getElementById('marketFeatureTitle'),content=document.getElementById('marketFeatureContent');
  const core=document.getElementById('marketCoreTools'),back=document.getElementById('marketFeatureBack');
  if(!cards||!panel||!title||!content||!core||!back)return;
  let mounted=null,generation=0,active=null;
  const names={chart:'نمودار و تحلیل قیمت',converter:'محاسبه‌گر نرخ',world:'اقتصاد جهان',gold:'پیش‌فاکتور طلا'};
  function close({scroll=false}={}) {
    generation++;
    if(mounted){mounted();mounted=null;}
    active=null;
    content.replaceChildren();content.hidden=false;
    core.hidden=true;
    for(const item of core.querySelectorAll('[data-core-feature]'))item.hidden=true;
    panel.hidden=true;
    for(const b of cards.querySelectorAll('[data-market-feature]'))b.setAttribute('aria-expanded','false');
    if(scroll)document.getElementById('marketFeatures')?.scrollIntoView({block:'start',behavior:'smooth'});
  }
  async function open(name,{force=false}={}) {
    if(!Object.prototype.hasOwnProperty.call(names,name))return;
    if(active===name&&!force){close({scroll:true});return;}
    if(active===name&&force){panel.scrollIntoView({block:'start',behavior:'smooth'});return;}
    close();active=name;
    const myGeneration=generation;
    const btn=cards.querySelector(`[data-market-feature="${name}"]`);
    btn?.setAttribute('aria-expanded','true');
    panel.hidden=false;title.textContent=names[name];
    const isCore=name==='chart'||name==='converter';
    core.hidden=!isCore;content.hidden=isCore;
    if(isCore){
      const target=core.querySelector(`[data-core-feature="${name}"]`);
      if(target)target.hidden=false;
      window.dispatchEvent(new CustomEvent('ct:core-tool-opened',{detail:{name}}));
    }else{
      content.textContent='در حال آماده‌سازی ابزار…';
    }
    panel.scrollIntoView({block:'start',behavior:'smooth'});
    if(isCore)return;
    try{
      const mod=name==='world'?await import('./world-economy.js'):await import('./gold-invoice.js');
      if(generation!==myGeneration||active!==name)return;
      const dispose=name==='world'?await mod.mountWorldEconomy(content):mod.mountGoldInvoice(content,{getGoldQuote});
      if(generation!==myGeneration||active!==name){dispose?.();return;}
      mounted=typeof dispose==='function'?dispose:null;
    }catch(error){
      if(generation!==myGeneration)return;
      content.replaceChildren();const note=document.createElement('p');note.className='ctmf-note ctmf-error';
      note.textContent='این ابزار بارگیری نشد. اتصال اینترنت یا نسخه برنامه را بررسی کنید.';content.append(note);
      console.error('CurrencyTel market feature',name,error);
    }
  }
  cards.addEventListener('click',event=>{
    const b=event.target.closest('button[data-market-feature]');if(b)open(b.dataset.marketFeature);
  });
  back.addEventListener('click',()=>close({scroll:true}));
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&!panel.hidden && !document.querySelector('.ct-select-menu:not([hidden])'))close({scroll:true});
  });
  window.addEventListener('hashchange',()=>{
    if(!['','#home','#prices','#tools'].includes(location.hash))close();
  });
  window.addEventListener('ct:open-market-tool',event=>open(event.detail?.name,{force:true}));
}
