/** CurrencyTel country indicators — no API keys or third-party scripts required.
 * World Bank data are historical/annual, and Frankfurter FX are reference rates.
 * Neither provider supplies Iranian cash/free-market quotes.
 */
export const METRICS = Object.freeze({
  inflation:{id:'FP.CPI.TOTL.ZG',title:'تورم سالانه',type:'percent'},
  gdp:{id:'NY.GDP.MKTP.CD',title:'تولید ناخالص داخلی',type:'gdp'},
  growth:{id:'NY.GDP.MKTP.KD.ZG',title:'رشد اقتصادی',type:'percent'},
  population:{id:'SP.POP.TOTL',title:'جمعیت',type:'population'},
  unemployment:{id:'SL.UEM.TOTL.ZS',title:'نرخ بیکاری',type:'percent'}
});
const memory=new Map();
async function requestJson(url,{signal,ttl=4*60*60*1000}={}) {
  const item=memory.get(url);
  if(item&&item.until>Date.now())return item.data;
  const abort=new AbortController();
  const onAbort=()=>abort.abort();
  signal?.addEventListener('abort',onAbort,{once:true});
  const timer=setTimeout(()=>abort.abort(),11000);
  try{
    const response=await fetch(url,{signal:abort.signal,cache:'default',headers:{Accept:'application/json'}});
    if(!response.ok)throw new Error(`دریافت اطلاعات ناموفق بود (${response.status})`);
    const data=await response.json();
    memory.set(url,{data,until:Date.now()+ttl});
    return data;
  }finally{clearTimeout(timer);signal?.removeEventListener('abort',onAbort);}
}
export async function getIndicator(iso2,key,{signal}={}) {
  const metric=METRICS[key];if(!metric)throw new RangeError('شاخص ناشناخته');
  const url=`https://api.worldbank.org/v2/country/${encodeURIComponent(iso2)}/indicator/${metric.id}?format=json&per_page=12&mrnev=1`;
  const data=await requestJson(url,{signal,ttl:24*60*60*1000});
  const row=Array.isArray(data?.[1])?data[1].find(x=>x&&Number.isFinite(x.value)):null;
  return row?{value:row.value,year:row.date,source:'World Bank'}:null;
}
export async function getReferenceFx(currency,{signal}={}) {
  if(!currency)return null;
  if(currency==='USD')return {value:1,date:null,source:'USD',currency:'USD'};
  const code=String(currency).toUpperCase();
  const url=`https://api.frankfurter.dev/v2/rate/USD/${encodeURIComponent(code)}`;
  const data=await requestJson(url,{signal,ttl:6*60*60*1000});
  return Number.isFinite(data?.rate)?{value:data.rate,date:data.date,source:'Frankfurter',currency:code}:null;
}
const format=(n,dec=2)=>new Intl.NumberFormat('fa-IR',{maximumFractionDigits:dec}).format(n);
export function displayMetric(value,type) {
  if(!Number.isFinite(value))return '—';
  if(type==='percent')return format(value,2)+'٪';
  if(type==='population')return value>=1e9?`${format(value/1e9,2)} میلیارد نفر`:value>=1e6?`${format(value/1e6,2)} میلیون نفر`:format(value,0)+' نفر';
  if(type==='gdp')return value>=1e12?`${format(value/1e12,2)} تریلیون دلار`:value>=1e9?`${format(value/1e9,2)} میلیارد دلار`:format(value,0)+' دلار';
  return format(value,3);
}
export function displayFx(value,currency) {
  return `${format(value,value>1000?2:4)} ${currency}`;
}
