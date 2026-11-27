import json, time, sys, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from currencytel.smartmoney import providers
from currencytel.smartmoney.analytics import analyze
OUT=ROOT/'data'/'smart-money.json'
MARKETS={'Binance':providers.binance,'Bybit':providers.bybit,'OKX':providers.okx,'Gate':providers.gate,'Kraken':providers.kraken,'Mempool':providers.chain}

def collect():
    try: old=json.loads(OUT.read_text(encoding='utf-8'))
    except (OSError,ValueError): old={}
    data=old.get('markets',{}); history=old.get('history',{}); status={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs={pool.submit(fn):name for name,fn in MARKETS.items()}
        for job in as_completed(jobs):
            name=jobs[job]
            try:
                m=job.result(); fields=[k for k in ('price','trades','book','candles','oi','funding','recent','blocks','fees') if m.get(k) is not None and m.get(k)!=[]]
                status[name]={'ok':bool(fields),'fields':fields,'errors':m.get('errors',{}),'time':int(time.time())}
                if fields:
                    if name=='Mempool': data[name]=m; continue
                    a={str(t):analyze(m,t) for t in (100000,500000,1000000)}
                    data[name]={'market':{k:v for k,v in m.items() if k not in ('trades','book','candles','spot','oih')},'analytics':a}
                    if m.get('price') is not None:
                        h=history.setdefault(name,[]); h.append({'time':m['time'],'price':m['price'],'score':a['100000']['score']}); history[name]=h[-288:]
            except Exception as e: status[name]={'ok':False,'errors':{'collector':str(e)},'time':int(time.time())}
    result={'version':'3.0','generated_at':int(time.time()),'markets':data,'history':history,'status':status}
    OUT.parent.mkdir(exist_ok=True); temp=OUT.with_suffix('.tmp'); temp.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding='utf-8'); os.replace(temp,OUT)
    print(json.dumps(status,ensure_ascii=False)); print('Published',OUT)
    if not any(v['ok'] for k,v in status.items() if k!='Mempool'):
        print('::warning::No exchange data fetched. See status in JSON; previous snapshots are retained.')
if __name__=='__main__': collect()
