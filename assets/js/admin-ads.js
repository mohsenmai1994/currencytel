/** CurrencyTel Ads Manager — GitHub Contents API publisher. Credentials are never persisted. */
const DEFINITIONS=[
  ['home_quick','خانه','زیر میانبرهای صفحه خانه'],
  ['market_between','بازار · بنر اصلی','پس از ابزارهای بازار، قبل از فهرست قیمت‌ها'],
  ['market_inline','بازار · پایان نمادها','بعد از فهرست قیمت‌ها، در عرض کامل صفحه'],
  ['news_inline','خبرها','پس از دومین خبر در فهرست سایر خبرها'],
  ['world_footer','اقتصاد جهان','زیر بخش کامل اطلاعات کشور، در عرض کامل'],
  ['gold_footer','پیش‌فاکتور طلا','بعد از ریز محاسبات و نتیجه پیش‌فاکتور'],
  ['tools_footer','نمودار و محاسبه‌گر نرخ','بعد از نتیجه نمودار یا محاسبه‌گر']
];
const FIELDS={banner:['enabled','title','url','image','alt','startAt','endAt'],link:['enabled','title','url','startAt','endAt']};
const BLANK=()=>({schema:1,updatedAt:'',placements:Object.fromEntries(DEFINITIONS.map(([id])=>[id,{
  banner:{enabled:false,title:'',url:'',image:'',alt:'',startAt:'',endAt:''},
  link:{enabled:false,title:'',url:'',startAt:'',endAt:''}
}]))});
const $=id=>document.getElementById(id);
let config=BLANK(),selected=DEFINITIONS[0][0],remoteLoaded=false,remoteSha=null,dirty=false,busy=false;
let uploads=new Map(); // holds selected File, preview object URL, crop values; no credential here.
const getSettings=()=>({
  owner:$('ghOwner').value.trim(),repo:$('ghRepo').value.trim(),branch:$('ghBranch').value.trim(),token:$('ghToken').value.trim()
});
function normalize(payload){
  if(!payload||payload.schema!==1||typeof payload.placements!=='object'||!payload.placements)throw Error('فرمت تنظیمات تبلیغات معتبر نیست.');
  // Important: retain every existing record and unknown setting, even those from
  // an older/future version. Never reconstruct the live manifest from BLANK().
  const normalized=structuredClone(payload);
  for(const [id] of DEFINITIONS){
    const baseline=BLANK().placements[id];
    if(!normalized.placements[id]||typeof normalized.placements[id]!=='object')normalized.placements[id]=baseline;
    const slot=normalized.placements[id];
    for(const kind of ['banner','link']){
      if(!slot[kind]||typeof slot[kind]!=='object')slot[kind]=structuredClone(baseline[kind]);
      for(const name of FIELDS[kind]){
        if(!(name in slot[kind]))slot[kind][name]=name==='enabled'?false:'';
      }
    }
  }
  return normalized;
}
function destination(value){
  if(typeof value!=='string')return null;
  const text=value.trim();
  if(/^#[A-Za-z][\w-]*$/.test(text))return text;
  try{const u=new URL(text);return u.protocol==='https:'&&!u.username&&!u.password?u.href:null;}catch{return null;}
}
function flagChanged(){dirty=true;$('publishState').textContent='تغییرات منتشرنشده';updateCounters();renderSlotButtons();}
function updateCounters(){
  let active=0;for(const [id] of DEFINITIONS)if(config.placements[id].banner.enabled)active++;
  $('activeCount').textContent=new Intl.NumberFormat('fa-IR').format(active)+' / '+new Intl.NumberFormat('fa-IR').format(DEFINITIONS.length);
  const slot=config.placements[selected];
  $('slotStatus').textContent=slot.banner.enabled?'فعال':'غیرفعال';
}
function renderSlotButtons(){
  const host=$('slots');host.replaceChildren();
  for(const [id,label] of DEFINITIONS){
    const slot=config.placements[id],n=Number(slot.banner.enabled);
    const button=document.createElement('button');button.className='slot-btn'+(id===selected?' active':'');button.type='button';
    const left=document.createElement('span'),title=document.createElement('b'),extra=document.createElement('small');
    title.textContent=label;extra.textContent=n?'فعال':'بدون تبلیغ';left.append(title,extra);
    const count=document.createElement('span');count.className='slot-count';count.textContent=n?'فعال':'خاموش';
    button.append(left,count);button.addEventListener('click',()=>{selected=id;renderSlotButtons();renderEditor();});host.append(button);
  }
}
function localInput(iso){
  if(!iso)return '';
  const d=new Date(iso);if(Number.isNaN(d.getTime()))return '';
  const pad=x=>String(x).padStart(2,'0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
const ADMIN_APP_ROOT=new URL('../../',import.meta.url);
const ADMIN_ADS_ROOT=new URL('assets/ads/',ADMIN_APP_ROOT);
function publishedImage(value){
  if(typeof value!=='string')return '';
  let raw=value.trim();if(/^\/assets\/ads\//.test(raw))raw='.'+raw;
  try{
    const u=new URL(raw,ADMIN_APP_ROOT);
    if(u.origin!==ADMIN_ADS_ROOT.origin||!u.pathname.startsWith(ADMIN_ADS_ROOT.pathname))return '';
    const file=u.pathname.slice(ADMIN_ADS_ROOT.pathname.length);
    return /^[A-Za-z0-9_-]+\.(?:webp|jpe?g|png)$/i.test(file)?new URL('assets/ads/'+file,ADMIN_APP_ROOT).href:'';
  }catch{return '';}
}
function getPicture(id=selected){
  const chosen=uploads.get(id);
  return chosen?chosen.url:publishedImage(config.placements[id].banner.image);
}
function renderImage(){
  const host=$('uploadVisual');host.replaceChildren();
  const src=getPicture();
  if(!src){const symbol=document.createElement('span');symbol.textContent='▧';const title=document.createElement('b');title.textContent='آپلود تصویر بنر';const hint=document.createElement('small');hint.textContent='PNG / JPG / WEBP · تا ۲۰MB';host.append(symbol,title,hint);}
  else{const image=document.createElement('img');image.src=src;image.alt='پیش‌نمایش تصویر انتخابی';image.style.objectPosition=`${uploads.get(selected)?.x??50}% ${uploads.get(selected)?.y??50}%`;host.append(image);}
  const pending=uploads.get(selected);
  $('cropControls').hidden=!pending;
  $('imageX').value=String(pending?.x??50);$('imageY').value=String(pending?.y??50);
}
function renderPreview(){
  const host=$('preview');host.replaceChildren();
  const record=config.placements[selected].banner,pic=getPicture();
  if(!record.enabled){
    const p=document.createElement('p');p.className='preview-empty';p.textContent='برای نمایش تبلیغ، کلید جایگاه را فعال کنید.';host.append(p);return;
  }
  if(!pic){
    const p=document.createElement('p');p.className='preview-empty';p.textContent='تصویر بنر را انتخاب کنید.';host.append(p);return;
  }
  const card=document.createElement('div');card.className='pv-card banner';
  const img=document.createElement('img');img.src=pic;img.alt='پیش‌نمایش بنر';
  img.style.objectPosition=`${uploads.get(selected)?.x??50}% ${uploads.get(selected)?.y??50}%`;
  const disclosure=document.createElement('span');disclosure.className='pv-disclosure';disclosure.textContent='تبلیغات';
  card.append(img,disclosure);host.append(card);
}
function renderEditor(){
  const def=DEFINITIONS.find(([id])=>id===selected),record=config.placements[selected];
  $('slotTitle').textContent=def[1];$('slotDescription').textContent=def[2];
  for(const field of document.querySelectorAll('[data-prop]')){
    const [kind,key]=field.dataset.prop.split('.');const value=record[kind][key];
    if(field.type==='checkbox')field.checked=Boolean(value);
    else field.value=(key==='startAt'||key==='endAt')?localInput(value):value;
  }
  updateCounters();renderImage();renderPreview();
}
function notify(message,error=false){$('feedback').textContent=message;$('feedback').classList.toggle('error',error);}
function discardUploads(){for(const value of uploads.values())URL.revokeObjectURL(value.url);uploads.clear();}
function validate(){
  for(const [id,label] of DEFINITIONS){
    const item=config.placements[id].banner;
    if(!item.enabled)continue;
    if(!destination(item.url))throw Error(`«${label}»: لینک باید HTTPS یا مسیری مانند #home باشد.`);
    if(!uploads.has(id)&&!publishedImage(item.image))throw Error(`«${label}»: تصویر بنر انتخاب نشده است.`);
    for(const key of ['startAt','endAt'])if(item[key]&&!Number.isFinite(Date.parse(item[key])))throw Error(`«${label}»: تاریخ نامعتبر است.`);
    if(item.startAt&&item.endAt&&Date.parse(item.startAt)>=Date.parse(item.endAt))throw Error(`«${label}»: زمان پایان باید بعد از شروع باشد.`);
  }
}
async function selectImage(file){
  if(!file)return;
  if(!['image/jpeg','image/png','image/webp'].includes(file.type))return notify('فرمت تصویر باید JPG، PNG یا WebP باشد.',true);
  if(file.size>20*1024*1024)return notify('تصویر ورودی نباید بیشتر از ۲۰ مگابایت باشد.',true);
  const objectUrl=URL.createObjectURL(file);const image=new Image();
  try{await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=objectUrl;});
    if(image.naturalWidth<300||image.naturalHeight<110)throw Error('ابعاد تصویر بسیار کوچک است.');
    if(image.naturalWidth*image.naturalHeight>40_000_000)throw Error('ابعاد تصویر بیش از حد بزرگ است.');
    const previous=uploads.get(selected);if(previous)URL.revokeObjectURL(previous.url);
    uploads.set(selected,{file,url:objectUrl,x:50,y:50});
    flagChanged();renderImage();renderPreview();notify('تصویر انتخاب شد؛ هنگام انتشار برش و فشرده می‌شود.');
  }catch(error){URL.revokeObjectURL(objectUrl);notify('تصویر خوانده نشد: '+(error.message||''),true);}
}
async function optimizedImage(upload){
  const image=new Image();await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=upload.url;});
  const w=1200,h=420,ratio=w/h,sw=image.naturalWidth,sh=image.naturalHeight;
  const cropW=Math.min(sw,sh*ratio),cropH=Math.min(sh,sw/ratio);
  const sx=(sw-cropW)*(upload.x/100),sy=(sh-cropH)*(upload.y/100);
  const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;
  const context=canvas.getContext('2d',{alpha:false});if(!context)throw Error('پردازش تصویر روی دستگاه ممکن نیست.');
  context.fillStyle='#0f2232';context.fillRect(0,0,w,h);context.drawImage(image,sx,sy,cropW,cropH,0,0,w,h);
  const toBlob=(type,quality)=>new Promise(resolve=>canvas.toBlob(resolve,type,quality));
  let blob=null,type='image/webp';
  for(const quality of [.92,.84,.74,.64,.54]){
    blob=await toBlob('image/webp',quality);
    if(!blob||blob.type!=='image/webp'){type='image/jpeg';blob=await toBlob(type,quality);}
    if(blob&&blob.size<=950_000)break;
  }
  if(!blob||blob.size>1_000_000)throw Error('تصویر پس از فشرده‌سازی هنوز بیشتر از ۱ مگابایت است.');
  return {blob,extension:type==='image/jpeg'?'jpg':'webp'};
}
function settingsValid(){
  const {owner,repo,branch,token}=getSettings();
  if(!/^[a-zA-Z0-9-]{1,100}$/.test(owner)||!/^[\w.-]{1,100}$/.test(repo)||!branch||/[\x00-\x1f]/.test(branch)||!token)throw Error('مالک، مخزن، شاخه و توکن معتبر GitHub را وارد کنید.');
  return {owner,repo,branch,token};
}
function b64(bytes){let output='';for(let i=0;i<bytes.length;i+=0x4000)output+=String.fromCharCode(...bytes.subarray(i,i+0x4000));return btoa(output);}
function decodeText(raw){const str=atob(raw.replace(/\s+/g,'')),a=Uint8Array.from(str,c=>c.charCodeAt(0));return new TextDecoder().decode(a);}
async function api(method,path,body=null){
  const {owner,repo,branch,token}=settingsValid();
  const route=path.split('/').map(encodeURIComponent).join('/');
  const url=`https://api.github.com/repos/${owner}/${repo}/contents/${route}`+(method==='GET'?`?ref=${encodeURIComponent(branch)}`:'');
  const res=await fetch(url,{method,cache:'no-store',headers:{'Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'X-GitHub-Api-Version':'2022-11-28',...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,referrerPolicy:'no-referrer'});
  if(res.status===404&&method==='GET')return null;
  if(!res.ok){let message='';try{const data=await res.json();message=data.message||'';}catch{}throw Error(`GitHub HTTP ${res.status}${message?' — '+message:''}`);}
  return res.json();
}
async function fetchRemoteFile(path){return api('GET',path);}
async function putRemoteFile(path,bytes,sha,description){
  const {branch}=settingsValid();
  return api('PUT',path,{message:description,content:b64(bytes),branch,...(sha?{sha}:{})});
}
function stringBytes(value){return new TextEncoder().encode(value);}
async function loadRemote(){
  if(busy)return;
  if(dirty&&!window.confirm('تغییرات ذخیره‌نشده با وضعیت مخزن جایگزین می‌شوند. ادامه می‌دهی؟'))return;
  busy=true;try{
    const result=await fetchRemoteFile('data/ads.json');
    if(result?.content){config=normalize(JSON.parse(decodeText(result.content)));remoteSha=result.sha;}
    else{throw Error('فایل data/ads.json در این شاخه پیدا نشد. برای جلوگیری از حذف آگهی‌های فعلی، انتشار متوقف شد. نام مخزن و شاخه را بررسی کن.');}
    remoteLoaded=true;dirty=false;discardUploads();renderSlotButtons();renderEditor();$('publishState').textContent='نسخه GitHub بارگذاری شد';notify('تنظیمات GitHub دریافت شد. لینک‌های متنی قدیمی در نسخه جدید نمایش داده نمی‌شوند؛ متن و آدرسشان فعلاً در فایل محفوظ است.');
  }catch(error){notify('خطا در دریافت فایل: '+error.message,true);}finally{busy=false;}
}
async function loadPublic(){
  if(busy)return;
  if(dirty&&!window.confirm('پیش‌نویس ذخیره‌نشده با نسخه عمومی جایگزین می‌شود. ادامه می‌دهی؟'))return;
  try{const response=await fetch('../data/ads.json?date='+Date.now(),{cache:'no-store'});if(!response.ok)throw Error('HTTP '+response.status);
    config=normalize(await response.json());remoteLoaded=false;remoteSha=null;dirty=false;discardUploads();renderSlotButtons();renderEditor();$('publishState').textContent='نسخه عمومی خوانده شد';notify('برای انتشار، ابتدا وضعیت را از GitHub هم دریافت کن.');
  }catch(error){notify('خطا در فایل عمومی: '+error.message,true);}
}
async function publish(){
  if(busy)return;
  try{
    validate();settingsValid();if(!remoteLoaded)throw Error('ابتدا روی «خواندن وضعیت از GitHub» بزن تا فایل اصلی و نسخه آن مشخص شود.');
    busy=true;$('publish').disabled=true;notify('در حال بررسی نسخه مخزن…');
    const latest=await fetchRemoteFile('data/ads.json');
    if((latest?.sha||null)!==remoteSha)throw Error('تنظیمات از آخرین بارگیری تغییر کرده‌اند. برای جلوگیری از بازنویسی، ابتدا دوباره وضعیت GitHub را دریافت کن.');
    const next=structuredClone(config);
    // Preserve all existing advertising records, including dormant legacy links.
    for(const [slot,entry] of uploads){
      notify(`در حال فشرده‌سازی و بارگذاری بنر «${DEFINITIONS.find(([id])=>id===slot)?.[1]}»…`);
      const {blob,extension}=await optimizedImage(entry);
      const unique=Date.now().toString(36)+'-'+Array.from(crypto.getRandomValues(new Uint8Array(4)),n=>n.toString(16).padStart(2,'0')).join('');
      const fileName=`assets/ads/${slot}-${unique}.${extension}`;
      await putRemoteFile(fileName,new Uint8Array(await blob.arrayBuffer()),null,'ads: upload '+slot+' banner');
      next.placements[slot].banner.image='./'+fileName;
    }
    next.updatedAt=new Date().toISOString();
    notify('در حال انتشار تنظیمات هشت جایگاه…');
    const result=await putRemoteFile('data/ads.json',stringBytes(JSON.stringify(next,null,2)+'\n'),remoteSha,'ads: update CurrencyTel placements');
    config=next;remoteSha=result.content?.sha||null;remoteLoaded=true;dirty=false;discardUploads();renderSlotButtons();renderEditor();$('publishState').textContent='در GitHub ثبت شد';
    notify('انتشار در GitHub موفق بود. در GitHub Pages تغییرات پس از تکمیل استقرار سایت و دریافت JSON جدید دیده می‌شوند.');
  }catch(error){notify('انتشار انجام نشد: '+error.message,true);}finally{busy=false;$('publish').disabled=false;}
}
function exportConfig(){
  if(uploads.size){notify('توجه: خروجی JSON تصویرهای انتخاب‌شده ولی منتشرنشده را ندارد. برای انتشار تصویرها از دکمه GitHub استفاده کن.',true);}
  const body=new Blob([JSON.stringify(config,null,2)+'\n'],{type:'application/json;charset=utf-8'});
  const url=URL.createObjectURL(body),a=document.createElement('a');a.href=url;a.download='currencytel-ads.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function importConfig(file){
  if(!file)return;
  try{if(file.size>200_000)throw Error('فایل بزرگ‌تر از حد مجاز است.');
    config=normalize(JSON.parse(await file.text()));discardUploads();remoteLoaded=false;remoteSha=null;flagChanged();renderEditor();notify('تنظیمات وارد شدند؛ برای انتشار باید ابتدا نسخه GitHub را بخوانی.');
  }catch(error){notify('خطا در واردکردن فایل: '+error.message,true);}
}
function init(){
  try{const v=JSON.parse(localStorage.getItem('ct-ad-repo-settings')||'{}');$('ghOwner').value=v.owner||'';$('ghRepo').value=v.repo||'';$('ghBranch').value=v.branch||'main';}catch{}
  for(const key of ['ghOwner','ghRepo','ghBranch'])$(key).addEventListener('change',()=>{
    const {owner,repo,branch}=getSettings();try{localStorage.setItem('ct-ad-repo-settings',JSON.stringify({owner,repo,branch}));}catch{}remoteLoaded=false;remoteSha=null;
  });
  $('ghToken').addEventListener('change',()=>{remoteLoaded=false;remoteSha=null;});
  document.querySelectorAll('[data-prop]').forEach(input=>input.addEventListener(input.type==='checkbox'?'change':'input',()=>{
    const [kind,key]=input.dataset.prop.split('.');
    let value=input.type==='checkbox'?input.checked:input.value;
    if(key==='startAt'||key==='endAt')value=value&&Number.isFinite(Date.parse(value))?new Date(value).toISOString():'';
    config.placements[selected][kind][key]=value;flagChanged();renderPreview();
  }));
  $('bannerFile').addEventListener('change',e=>{selectImage(e.target.files?.[0]);e.target.value='';});
  $('chooseImage').addEventListener('click',()=>$('bannerFile').click());
  $('removeImage').addEventListener('click',()=>{
    const prev=uploads.get(selected);if(prev)URL.revokeObjectURL(prev.url);uploads.delete(selected);
    config.placements[selected].banner.image='';flagChanged();renderImage();renderPreview();
  });
  for(const [id,key] of [['imageX','x'],['imageY','y']])$(id).addEventListener('input',e=>{
    const entry=uploads.get(selected);if(entry){entry[key]=Number(e.target.value);renderPreview();
      const preview=$('uploadVisual').querySelector('img');if(preview)preview.style.objectPosition=`${entry.x}% ${entry.y}%`;
    }
  });
  const drop=$('uploadDrop');drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('drag');});
  drop.addEventListener('dragleave',()=>drop.classList.remove('drag'));
  drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('drag');selectImage(e.dataTransfer?.files?.[0]);});
  $('loadRemote').addEventListener('click',loadRemote);$('loadPublic').addEventListener('click',loadPublic);
  $('publish').addEventListener('click',publish);$('exportJson').addEventListener('click',exportConfig);
  $('importJson').addEventListener('change',e=>{importConfig(e.target.files?.[0]);e.target.value='';});
  $('resetDraft').addEventListener('click',()=>{
    if(!window.confirm('همه تغییرات منتشرنشده پاک شوند؟'))return;
    config=BLANK();discardUploads();remoteLoaded=false;remoteSha=null;flagChanged();renderSlotButtons();renderEditor();notify('پیش‌نویس بازنشانی شد. این تغییر هنوز در GitHub منتشر نشده است.');
  });
  renderSlotButtons();renderEditor();loadPublic();
}
init();
