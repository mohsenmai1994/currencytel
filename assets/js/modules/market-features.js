/** Market-tab feature controller: isolated from quote/news/chart lifecycle. */
export function initMarketFeatures({getGoldQuote}={}) {
  const cards=document.getElementById('marketFeatureCards'),panel=document.getElementById('marketFeaturePanel');
  const title=document.getElementById('marketFeatureTitle'),content=document.getElementById('marketFeatureContent');
  const back=document.getElementById('marketFeatureBack');
  if(!cards||!panel||!title||!content||!back)return;
  let mounted=null,generation=0,active=null;
  function close({scroll=false}={}){
    generation++;if(mounted){mounted();mounted=null;}
    active=null;content.replaceChildren();panel.hidden=true;
    for(const b of cards.querySelectorAll('button[data-market-feature]'))b.setAttribute('aria-expanded','false');
    if(scroll)document.getElementById('marketFeatures')?.scrollIntoView({block:'start',behavior:'smooth'});
  }
  async function open(name){
    if(active===name){close({scroll:true});return;}
    close();active=name;
    const myGeneration=generation;
    const btn=cards.querySelector(`button[data-market-feature="${name}"]`);
    if(btn)btn.setAttribute('aria-expanded','true');
    panel.hidden=false;title.textContent=name==='world'?'اقتصاد جهان':'پیش‌فاکتور طلا';
    content.textContent='در حال آماده‌سازی ابزار…';
    panel.scrollIntoView({block:'start',behavior:'smooth'});
    try{
      const module=name==='world'
        ? await import('./world-economy.js')
        : await import('./gold-invoice.js');
      if(generation!==myGeneration||active!==name)return;
      const dispose=name==='world'?await module.mountWorldEconomy(content):module.mountGoldInvoice(content,{getGoldQuote});
      if(generation!==myGeneration||active!==name){dispose?.();return;}
      mounted=typeof dispose==='function'?dispose:null;
    }catch(error){
      if(generation!==myGeneration)return;
      content.replaceChildren();const note=document.createElement('p');note.className='ctmf-note ctmf-error';
      note.textContent='این بخش بارگیری نشد. اتصال اینترنت یا نسخه برنامه را بررسی کنید و دوباره تلاش کنید.';content.append(note);
      console.error('CurrencyTel market feature',name,error);
    }
  }
  cards.addEventListener('click',event=>{
    const b=event.target.closest('button[data-market-feature]');if(!b)return;
    open(b.dataset.marketFeature);
  });
  back.addEventListener('click',()=>close({scroll:true}));
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!panel.hidden)close({scroll:true});});
  window.addEventListener('hashchange',()=>{
    if(!['','#home','#prices'].includes(location.hash))close();
  });
}
