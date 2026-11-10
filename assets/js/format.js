export const categories={currency:'ارز',coin:'سکه',gold:'طلا',crypto:'رمزارز',energy:'انرژی',metal:'فلزات پایه',agriculture:'کشاورزی',index:'شاخص‌های جهانی',commodity:'کالاهای جهانی',bond:'اوراق',forex:'فارکس'};
export const categoryIcons={currency:'$',coin:'◉',gold:'✧',crypto:'₿',energy:'◈',metal:'⬡',agriculture:'❋',index:'⌁',commodity:'◆',bond:'▣',forex:'↗'};
export function number(value,maximumFractionDigits=8){
  if(value===null||value===undefined||value==='')return '—';
  const n=Number(value);
  if(!Number.isFinite(n))return '—';
  return new Intl.NumberFormat('en-US',{maximumFractionDigits:Math.abs(n)<0.01?12:maximumFractionDigits}).format(n);
}
export function money(item){return number(item?.value);} 
export function clean(text){return String(text||'').replace(/[ي]/g,'ی').replace(/ك/g,'ک').toLowerCase().trim();}
export function safe(text){return String(text??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
export function when(value){
  if(!value)return 'زمان ثبت داده قبلی مشخص نیست';
  const date=new Date(value);
  if(!Number.isFinite(date.getTime()))return 'نامشخص';
  return date.toLocaleString('fa-IR',{timeZone:'Asia/Tehran',year:'numeric',month:'long',day:'numeric',hour:'2-digit',minute:'2-digit'});
}
export function ageMinutes(value){const n=Date.parse(value);return Number.isFinite(n)?Math.max(0,Math.floor((Date.now()-n)/60000)):Infinity;}
export function changeText(v){
  if(v===undefined||v===null||v==='')return ['—','flat'];
  const n=Number(v);
  if(!Number.isFinite(n))return ['—','flat'];
  return [(n>0?'+':'')+number(n,2)+'%',n>0?'up':n<0?'down':'flat'];
}
