/** CurrencyTel v6: viewport-anchored accessible dropdowns; native selects preserve existing data-binding. */
const enhanced=new WeakMap();
let opened=null;
let uid=0;
const create=(tag,cls)=>{const el=document.createElement(tag);el.className=cls;return el;};
function closeMenu(item,{focus=false}={}){
  if(!item)return;
  item.menu.hidden=true;
  item.trigger.setAttribute('aria-expanded','false');
  item.wrap.classList.remove('ct-select-open');
  if(opened===item)opened=null;
  if(focus&&item.trigger.isConnected)item.trigger.focus({preventScroll:true});
}
function synchronize(item){
  const {select,caption,trigger,list}=item;
  caption.textContent=select.selectedOptions[0]?.textContent?.trim()||'انتخاب کنید';
  trigger.disabled=select.disabled;
  for(const button of list.querySelectorAll('[data-option-value]')){
    const chosen=button.dataset.optionValue===select.value;
    button.classList.toggle('selected',chosen);
    button.setAttribute('aria-selected',String(chosen));
  }
}
function buildList(item){
  item.list.replaceChildren();
  for(const option of Array.from(item.select.options)){
    const btn=create('button','ct-select-option');btn.type='button';
    btn.dataset.optionValue=option.value;
    btn.setAttribute('role','option');
    btn.textContent=option.textContent;btn.disabled=option.disabled;
    item.list.append(btn);
  }
  item.searchWrap.hidden=item.select.options.length<=14;
  item.search.value='';
  synchronize(item);
}
function positionMenu(item){
  if(opened!==item||item.menu.hidden)return;
  if(!item.trigger.isConnected||item.trigger.getClientRects().length===0){closeMenu(item);return;}
  const rect=item.trigger.getBoundingClientRect();
  const vv=window.visualViewport;
  const x0=vv?.offsetLeft||0, y0=vv?.offsetTop||0;
  const vw=vv?.width||window.innerWidth, vh=vv?.height||window.innerHeight;
  const inset=10,gap=6;
  const width=Math.min(Math.max(rect.width,Math.min(280,vw-2*inset)),vw-2*inset);
  const left=Math.max(x0+inset,Math.min(rect.right-width,x0+vw-inset-width));
  const below=y0+vh-rect.bottom-gap-inset;
  const above=rect.top-y0-gap-inset;
  const onTop=below<210&&above>below+45;
  const height=Math.max(90,Math.min(340,onTop?above:below));
  const top=onTop?Math.max(y0+inset,rect.top-gap-height):Math.min(y0+vh-inset-height,rect.bottom+gap);
  Object.assign(item.menu.style,{left:`${Math.round(left)}px`,top:`${Math.round(top)}px`,width:`${Math.round(width)}px`,maxHeight:`${Math.round(height)}px`});
  item.menu.classList.toggle('ct-popup-above',onTop);
}
function openMenu(item){
  if(item.select.disabled)return;
  if(opened&&opened!==item)closeMenu(opened);
  if(!item.menu.isConnected)document.body.append(item.menu);
  opened=item;
  buildList(item);
  item.menu.hidden=false;
  item.trigger.setAttribute('aria-expanded','true');
  item.wrap.classList.add('ct-select-open');
  positionMenu(item);
  // On touch devices autofocus causes the virtual keyboard to resize/shift the whole app.
  if(!matchMedia('(pointer:coarse)').matches){
    if(!item.searchWrap.hidden)item.search.focus({preventScroll:true});
  }
}
function selectItem(item,value){
  const {select}=item;
  if(select.value!==value){
    select.value=value;
    select.dispatchEvent(new Event('change',{bubbles:true}));
  }
  synchronize(item);closeMenu(item,{focus:true});
}
function enhance(select){
  if(enhanced.has(select)||!select.parentNode)return;
  const wrap=create('div','ct-select-shell');
  select.parentNode.insertBefore(wrap,select);wrap.append(select);
  select.classList.add('ct-native-select');
  const trigger=create('button','ct-select-trigger');trigger.type='button';
  trigger.setAttribute('aria-haspopup','listbox');trigger.setAttribute('aria-expanded','false');
  const label=select.getAttribute('aria-label')||select.closest('label')?.textContent?.trim()||'انتخاب گزینه';
  trigger.setAttribute('aria-label',label);
  const caption=create('span','ct-select-caption');
  const chevron=create('span','ct-select-chevron');chevron.setAttribute('aria-hidden','true');
  chevron.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="m6 9 6 6 6-6"/></svg>';
  trigger.append(caption,chevron);
  const menu=create('div','ct-select-menu');menu.hidden=true;menu.dir='rtl';
  const searchWrap=create('div','ct-select-search-wrap');
  const search=create('input','ct-select-search');search.type='search';search.placeholder='جست‌وجو در گزینه‌ها…';search.setAttribute('aria-label','جست‌وجو در فهرست');
  searchWrap.append(search);
  const list=create('div','ct-select-list');list.setAttribute('role','listbox');
  list.id=`ct-popup-${++uid}`;trigger.setAttribute('aria-controls',list.id);
  menu.append(searchWrap,list);wrap.append(trigger);document.body.append(menu);
  const item={select,wrap,trigger,caption,menu,searchWrap,search,list};enhanced.set(select,item);
  buildList(item);
  trigger.addEventListener('click',()=>opened===item?closeMenu(item,{focus:true}):openMenu(item));
  trigger.addEventListener('keydown',e=>{
    if(['ArrowDown','ArrowUp','Enter',' '].includes(e.key)){
      e.preventDefault();if(opened!==item)openMenu(item);
      item.list.querySelector('.selected')?.focus({preventScroll:true});
    }
  });
  list.addEventListener('click',e=>{
    const button=e.target.closest('[data-option-value]');
    if(button&&!button.disabled)selectItem(item,button.dataset.optionValue);
  });
  list.addEventListener('keydown',e=>{
    const choices=Array.from(list.querySelectorAll('.ct-select-option:not([hidden]):not(:disabled)'));
    const i=choices.indexOf(document.activeElement);
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){
      e.preventDefault();choices[Math.max(0,Math.min(choices.length-1,i+(e.key==='ArrowDown'?1:-1)))]?.focus({preventScroll:true});
    }
    if(e.key==='Home'){e.preventDefault();choices[0]?.focus({preventScroll:true});}
    if(e.key==='End'){e.preventDefault();choices.at(-1)?.focus({preventScroll:true});}
    if(e.key==='Enter'||e.key===' '){e.preventDefault();document.activeElement?.click();}
    if(e.key==='Escape'){e.preventDefault();closeMenu(item,{focus:true});}
  });
  menu.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();closeMenu(item,{focus:true});}});
  search.addEventListener('input',()=>{
    const q=search.value.trim().toLocaleLowerCase('fa');
    list.querySelectorAll('[data-option-value]').forEach(opt=>{opt.hidden=!opt.textContent.toLocaleLowerCase('fa').includes(q);});
  });
  select.addEventListener('change',()=>synchronize(item));
  new MutationObserver(()=>buildList(item)).observe(select,{childList:true,subtree:true,characterData:true});
}
export function syncCustomSelects(){
  document.querySelectorAll('select').forEach(select=>{
    if(!enhanced.has(select))enhance(select);
    else synchronize(enhanced.get(select));
  });
}
export function initCustomSelects(){
  syncCustomSelects();
  document.addEventListener('pointerdown',e=>{
    if(opened&&!opened.wrap.contains(e.target)&&!opened.menu.contains(e.target))closeMenu(opened);
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&opened){e.stopPropagation();closeMenu(opened,{focus:true});}
  },true);
  for(const target of [window,window.visualViewport].filter(Boolean)){
    target.addEventListener('resize',()=>{if(opened)positionMenu(opened);},{passive:true});
    target.addEventListener('scroll',()=>{if(opened)positionMenu(opened);},{passive:true});
  }
  window.addEventListener('hashchange',()=>{if(opened)closeMenu(opened);});
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&opened)closeMenu(opened);});
  new MutationObserver(records=>{
    for(const record of records){
      for(const node of record.addedNodes){
        if(!(node instanceof Element))continue;
        if(node.matches('select')&&!enhanced.has(node))enhance(node);
        node.querySelectorAll?.('select').forEach(sel=>{if(!enhanced.has(sel))enhance(sel);});
      }
    }
  }).observe(document.body,{childList:true,subtree:true});
}
