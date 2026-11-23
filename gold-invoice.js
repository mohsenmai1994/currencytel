import {calculateGoldInvoice,formatToman,VAT_DEFAULT_1405} from './gold-calculator.js';
import {parseLocalizedNumber,when} from '../format.js';
const $=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
const fnum=n=>new Intl.NumberFormat('fa-IR',{maximumFractionDigits:3}).format(n);
function field(label,name,{value='',type='text',choices=null,placeholder=''}={}) {
  const wrapper=$('label','ctmf-field'),title=$('span','ctmf-field-label',label),control=$(choices?'select':'input','ctmf-input');
  control.name=name;
  if(choices){for(const [v,caption] of choices){const option=$('option','',caption);option.value=v;control.append(option);}control.value=value;}
  else{control.type=type;control.inputMode='decimal';control.autocomplete='off';control.value=value;control.placeholder=placeholder;control.spellcheck=false;}
  wrapper.append(title,control);return {wrapper,control};
}
export function mountGoldInvoice(container,{getGoldQuote}={}) {
  container.replaceChildren();
  const root=$('div','ctmf-gold');
  root.append($('p','ctmf-intro','قیمت طلا، اجرت ساخت، سود فروشنده و مالیات را جداگانه محاسبه کنید. همه مبالغ به تومان هستند.'));
  const form=$('form','ctmf-gold-form');form.noValidate=true;
  const fieldGrid=$('div','ctmf-form-grid'),inputs={};
  const spec=[
    ['قیمت هر گرم طلای ۱۸ عیار (تومان)','gram18',{placeholder:'مثلاً ۱۵۰۰۰۰۰۰'}],
    ['وزن طلا (گرم)','weight',{placeholder:'مثلاً ۳٫۵'}],
    ['عیار طلا','purity',{value:'750',choices:[['750','۱۸ عیار (۷۵۰)'],['875','۲۱ عیار (۸۷۵)'],['916','۲۲ عیار (۹۱۶)'],['999','۲۴ عیار (۹۹۹)']]}],
    ['نوع اجرت ساخت','makingMode',{value:'percent',choices:[['percent','درصد از ارزش طلا'],['perGram','تومان به ازای هر گرم'],['fixed','مبلغ ثابت (تومان)']]}],
    ['مقدار اجرت ساخت','makingValue',{value:'0',placeholder:'۰'}],
    ['سود فروشنده (درصد)','profitRate',{value:'7'}],
    ['حق‌العمل (تومان)','commission',{value:'0'}],
    ['مالیات بر اجرت و سود (درصد)','vatRate',{value:String(VAT_DEFAULT_1405)}],
    ['تخفیف نهایی پس از مالیات (تومان)','discount',{value:'0'}]
  ];
  for(const [label,name,params] of spec){const {wrapper,control}=field(label,name,params);inputs[name]=control;fieldGrid.append(wrapper);}
  const rateBar=$('div','ctmf-rate-bar');const rateBtn=$('button','ctmf-btn ctmf-btn-soft','↻ دریافت آخرین نرخ کرنسی‌تل');rateBtn.type='button';
  const rateMeta=$('small','ctmf-muted','می‌توانید نرخ هر گرم را دستی هم وارد کنید.');
  rateBar.append(rateBtn,rateMeta);form.append(rateBar,fieldGrid);
  const notice=$('p','ctmf-muted','فرمول قیمت عیارهای مختلف بر مبنای نرخ هر گرم طلای ۱۸ عیار است. در محاسبه، مالیات فقط روی اجرت ساخت، سود فروشنده و حق‌العمل اعمال می‌شود.');
  form.append(notice);
  const result=$('section','ctmf-invoice-result');result.setAttribute('aria-labelledby','ctmfInvoiceTitle');
  const resultHeader=$('div','ctmf-invoice-head'),title=$('h3','', 'ریز پیش‌فاکتور طلا'),date=$('small','ctmf-muted','');
  title.id='ctmfInvoiceTitle';resultHeader.append(title,date);result.append(resultHeader);
  const status=$('p','ctmf-note','برای شروع، وزن و قیمت طلا را وارد کنید.');status.setAttribute('aria-live','polite');result.append(status);
  const rows=[['ارزش اصل طلا','base'],['اجرت ساخت','making'],['سود فروشنده','profit'],['حق‌العمل','commission'],['مالیات ارزش افزوده خدمات','vat'],['تخفیف پس از مالیات','discount']];
  const table=$('table','ctmf-invoice-table');table.setAttribute('aria-label','ریز محاسبات');const body=$('tbody');const cells={};
  rows.forEach(([label,key])=>{const tr=$('tr'),th=$('th','',label),td=$('td','ctmf-price','—');th.scope='row';td.dataset.key=key;cells[key]=td;tr.append(th,td);body.append(tr);});table.append(body);result.append(table);
  const total=$('div','ctmf-invoice-total'),totalLabel=$('span','', 'مبلغ نهایی'),totalValue=$('strong','', '—');total.append(totalLabel,totalValue);result.append(total);
  const actions=$('div','ctmf-invoice-actions'),copy=$('button','ctmf-btn ctmf-btn-soft','کپی ریز فاکتور'),print=$('button','ctmf-btn','چاپ / ذخیره PDF');
  copy.type=print.type='button';copy.disabled=print.disabled=true;actions.append(copy,print);result.append(actions);
  result.append($('p','ctmf-invoice-legal','این یک پیش‌فاکتور محاسباتی است؛ فاکتور رسمی مالیاتی و مدرک خرید محسوب نمی‌شود. نرخ مالیات و مفاد فاکتور را با فروشنده تطبیق دهید.'));
  root.append(form,result);container.append(root);
  let current=null,disposed=false;
  const num=n=>parseLocalizedNumber(inputs[n].value);
  function calculate(){
    if(disposed)return;
    current=null;
    if(!inputs.gram18.value.trim()||!inputs.weight.value.trim()){
      status.textContent='برای شروع، قیمت هر گرم و وزن طلا را وارد کنید.';
      status.classList.remove('ctmf-error');
    }else{
      try{
        current=calculateGoldInvoice(Object.fromEntries(Object.keys(inputs).map(k=>[k,k==='purity'||k==='makingMode'?inputs[k].value:num(k)])));
        status.textContent='مبالغ به تومان هستند و پس از محاسبه هر جزء گرد شده‌اند.';status.classList.remove('ctmf-error');
      }catch(error){status.textContent=error.message||'مقادیر واردشده نامعتبر هستند.';status.classList.add('ctmf-error');}
    }
    for(const key of Object.keys(cells))cells[key].textContent=current?`${key==='discount'?'− ':''}${formatToman(current[key])}`:'—';
    totalValue.textContent=current?formatToman(current.total):'—';copy.disabled=print.disabled=!current;
    date.textContent=current?new Intl.DateTimeFormat('fa-IR',{dateStyle:'medium',timeStyle:'short'}).format(new Date()):'';
  }
  for(const control of Object.values(inputs)){
    control.addEventListener('input',calculate);control.addEventListener('change',calculate);
  }
  form.addEventListener('submit',event=>event.preventDefault());
  function applyMarketPrice(){
    const quote=getGoldQuote?.();const value=Number(quote?.value);
    if(!quote||!Number.isFinite(value)||value<=0||quote.unit!=='تومان'){
      rateMeta.textContent='نرخ معتبر طلای ۱۸ عیار در دسترس نیست. قیمت را دستی وارد کنید.';return;
    }
    inputs.gram18.value=String(value);
    rateMeta.textContent=`نرخ ثبت‌شده: ${fnum(value)} تومان${quote.received_at?` · ${when(quote.received_at)}`:''}`;
    calculate();
  }
  rateBtn.addEventListener('click',applyMarketPrice);
  copy.addEventListener('click',async()=>{
    if(!current)return;
    const body=['کرنسی‌تل | پیش‌فاکتور محاسباتی طلا',...rows.map(([title,key])=>`${title}: ${formatToman(current[key])}`),`عیار: ${current.purity} از ۱۰۰۰`,`وزن: ${fnum(current.weight)} گرم`,`مبلغ نهایی: ${formatToman(current.total)}`,'غیررسمی؛ صرفاً جهت برآورد'].join('\n');
    const old=copy.textContent;
    try{
      if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(body);}else{
        const ta=$('textarea');ta.value=body;ta.style.position='fixed';ta.style.opacity='0';document.body.append(ta);ta.select();const ok=document.execCommand('copy');ta.remove();if(!ok)throw new Error('Copy not available');
      }
      copy.textContent='کپی شد ✓';
    }catch{copy.textContent='کپی ممکن نشد';}
    setTimeout(()=>{if(!disposed)copy.textContent=old;},2100);
  });
  print.addEventListener('click',()=>{if(current)window.print();});
  applyMarketPrice();calculate();
  return ()=>{disposed=true;root.remove();};
}
