/** Accessible themed dropdowns. Underlying <select>s remain source of truth for existing app code. */
const enhanced=new WeakMap();
let opened=null;
const by=(tag,className)=>{const node=document.createElement(tag);node.className=className;return node;};
function closeMenu(item,{focus=false}={}){
  if(!item)return;
  item.menu.hidden=true;item.trigger.setAttribute('aria-expanded','false');
  item.wrap.classList.remove('ct-select-open','ct-select-above');
  if(opened===item)opened=null;
  if(focus)item.trigger.focus();
}
function selectItem(item,value){
  const {select}=item;
  if(select.value!==value){select.value=value;select.dispatchEvent(new Event('change',{bubbles:true}));}
  synchronize(item);closeMenu(item,{focus:true});
}
function synchronize(item){
  const select=item.select;
  const selected=select.selectedOptions[0];
  item.caption.textContent=selected?.textContent?.trim()||'انتخاب کنید';
  item.trigger.disabled=select.disabled;
  for(const button of item.list.querySelectorAll('[data-option-value]')){
    const chosen=button.dataset.optionValue===select.value;
    button.classList.toggle('selected',chosen);
    button.setAttribute('aria-selected',String(chosen));
  }
}
function buildList(item){
  const select=item.select;
  const options=Array.from(select.options);
  // Rebuilding only when option markup changes (not when data updates) avoids unnecessary DOM churn.
  item.list.replaceChildren();
  for(const option of options){
    const btn=by('button','ct-select-option');btn.type='button';btn.setAttribute('role','option');
    btn.dataset.optionValue=option.value;btn.textContent=option.textContent;btn.disabled=option.disabled;
    item.list.append(btn);
  }
  item.searchWrap.hidden=options.length<=14;
  item.search.value='';
  synchronize(item);
}
function openMenu(item){
  if(opened&&opened!==item)closeMenu(opened);
  if(item.select.disabled)return;
  opened=item;
  buildList(item);
  const rect=item.trigger.getBoundingClientRect();
  const below=window.innerHeight-rect.bottom;
  item.wrap.classList.toggle('ct-select-above',below<240&&rect.top>below+80);
  item.menu.hidden=false;item.trigger.setAttribute('aria-expanded','true');item.wrap.classList.add('ct-select-open');
  if(!item.searchWrap.hidden)item.search.focus();
  else item.list.querySelector('.selected')?.focus({preventScroll:true});
}
function enhance(select){
  if(enhanced.has(select))return;
  const wrapper=by('div','ct-select-shell');
  select.parentNode.insertBefore(wrapper,select);wrapper.append(select);
  select.classList.add('ct-native-select');
  const trigger=by('button','ct-select-trigger');trigger.type='button';trigger.setAttribute('aria-haspopup','listbox');
  trigger.setAttribute('aria-expanded','false');
  const label=select.getAttribute('aria-label')||select.closest('label')?.textContent?.trim()||'انتخاب گزینه';
  trigger.setAttribute('aria-label',label);
  const caption=by('span','ct-select-caption');
  const chevron=by('span','ct-select-chevron');chevron.setAttribute('aria-hidden','true');
  chevron.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';
  trigger.append(caption,chevron);
  const menu=by('div','ct-select-menu');menu.hidden=true;
  const searchWrap=by('div','ct-select-search-wrap');
  const search=by('input','ct-select-search');search.type='search';search.placeholder='جست‌وجو در گزینه‌ها…';search.setAttribute('aria-label','جست‌وجو در فهرست');
  searchWrap.append(search);const list=by('div','ct-select-list');list.setAttribute('role','listbox');
  const listId=`ct-list-${document.querySelectorAll('.ct-select-shell').length+1}`;
  list.id=listId;trigger.setAttribute('aria-controls',listId);
  menu.append(searchWrap,list);wrapper.append(trigger,menu);
  const item={select,wrap:wrapper,trigger,caption,menu,list,searchWrap,search};enhanced.set(select,item);
  buildList(item);
  trigger.addEventListener('click',()=>{if(opened===item)closeMenu(item,{focus:true});else openMenu(item);});
  trigger.addEventListener('keydown',e=>{
    if(['ArrowDown','ArrowUp','Enter',' '].includes(e.key)){e.preventDefault();openMenu(item);}
  });
  list.addEventListener('click',e=>{const option=e.target.closest('[data-option-value]');if(option&&!option.disabled)selectItem(item,option.dataset.optionValue);});
  list.addEventListener('keydown',e=>{
    const choices=Array.from(list.querySelectorAll('.ct-select-option:not([hidden]):not(:disabled)'));
    const i=choices.indexOf(document.activeElement);
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();choices[Math.min(Math.max(i+(e.key==='ArrowDown'?1:-1),0),choices.length-1)]?.focus();}
    if(e.key==='Home'){e.preventDefault();choices[0]?.focus();}
    if(e.key==='End'){e.preventDefault();choices[choices.length-1]?.focus();}
    if(e.key==='Enter'||e.key===' '){e.preventDefault();document.activeElement?.click();}
    if(e.key==='Escape'){e.preventDefault();closeMenu(item,{focus:true});}
  });
  search.addEventListener('input',()=>{
    const query=search.value.trim().toLocaleLowerCase('fa');
    list.querySelectorAll('[data-option-value]').forEach(opt=>{opt.hidden=!opt.textContent.toLocaleLowerCase('fa').includes(query);});
  });
  menu.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();closeMenu(item,{focus:true});}});
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
    if(opened&&!opened.wrap.contains(e.target))closeMenu(opened);
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&opened){e.stopPropagation();closeMenu(opened,{focus:true});}
  },true);
  window.addEventListener('hashchange',()=>{if(opened)closeMenu(opened);});
  const observer=new MutationObserver(records=>{
    for(const record of records){
      for(const node of record.addedNodes){
        if(!(node instanceof Element))continue;
        if(node.matches('select')&&!enhanced.has(node))enhance(node);
        node.querySelectorAll?.('select').forEach(sel=>{if(!enhanced.has(sel))enhance(sel);});
      }
    }
  });
  observer.observe(document.body,{childList:true,subtree:true});
}
