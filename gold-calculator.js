/**
 * CurrencyTel — pure gold pre-invoice calculator.
 * All monetary inputs and returned amounts are in TOMAN (not rial).
 * Purity uses the 1000-based millesimal scale: 750 = 18K, 999 = 24K.
 * VAT is applied ONLY to making charge + seller margin + commission.
 */
export const VAT_DEFAULT_1405 = 10;
const cash = value => Math.round(value);
function nonNegative(v,label,{positive=false,max=Number.MAX_SAFE_INTEGER}={}) {
  if (v === '' || v === null || v === undefined || typeof v === 'boolean') throw new RangeError(`${label} را وارد کنید.`);
  const n=Number(v);
  if (!Number.isFinite(n) || n<0 || (positive&&n===0) || n>max) throw new RangeError(`${label} نامعتبر است.`);
  return n;
}
export function calculateGoldInvoice(raw) {
  const gram18=nonNegative(raw.gram18,'قیمت هر گرم طلای ۱۸ عیار',{positive:true,max:1e12});
  const grams=nonNegative(raw.weight,'وزن طلا',{positive:true,max:100000});
  const purity=nonNegative(raw.purity??750,'عیار',{positive:true,max:1000});
  const mode=raw.makingMode??'percent';
  if(!['percent','perGram','fixed'].includes(mode))throw new RangeError('روش اجرت نامعتبر است.');
  const makingInput=nonNegative(raw.makingValue??0,'اجرت ساخت',{max:1e12});
  if(mode==='percent'&&makingInput>1000)throw new RangeError('درصد اجرت ساخت نامعتبر است.');
  const profitRate=nonNegative(raw.profitRate??7,'درصد سود فروشنده',{max:100});
  const commission=nonNegative(raw.commission??0,'حق‌العمل',{max:1e12});
  const vatRate=nonNegative(raw.vatRate??VAT_DEFAULT_1405,'درصد مالیات',{max:100});
  const discount=nonNegative(raw.discount??0,'تخفیف',{max:1e12});

  const base=cash(gram18 * grams * (purity/750));
  const making=cash(mode==='percent'?base*makingInput/100:mode==='perGram'?grams*makingInput:makingInput);
  const profit=cash((base+making)*profitRate/100);
  const serviceCommission=cash(commission);
  const taxable=making+profit+serviceCommission;
  const vat=cash(taxable*vatRate/100);
  const beforeDiscount=base+making+profit+serviceCommission+vat;
  if(!Number.isSafeInteger(beforeDiscount)||beforeDiscount>Number.MAX_SAFE_INTEGER)throw new RangeError('مبلغ محاسبه‌شده خارج از محدوده مجاز است.');
  const roundedDiscount=cash(discount);
  if(roundedDiscount>beforeDiscount)throw new RangeError('تخفیف نمی‌تواند از جمع فاکتور بیشتر باشد.');
  const total=beforeDiscount-roundedDiscount;
  return {base,making,profit,commission:serviceCommission,taxable,vat,discount:roundedDiscount,total,
    beforeDiscount,gram18,weight:grams,purity,profitRate,vatRate,makingMode:mode,makingValue:makingInput};
}
export function formatToman(value) {return new Intl.NumberFormat('fa-IR',{maximumFractionDigits:0}).format(value)+' تومان';}
