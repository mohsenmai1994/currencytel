import json, urllib.request, urllib.parse, time
from concurrent.futures import ThreadPoolExecutor

def get(base,path,params=None):
    url=base+path+('?' + urllib.parse.urlencode(params) if params else '')
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CurrencyTel-SmartMoney/1.0','Accept':'application/json'}),timeout=8) as r:
        return json.load(r)

def binance():
    base='https://fapi.binance.com'; spot='https://api.binance.com'; sym={'symbol':'BTCUSDT'}
    jobs={'ticker':(base,'/fapi/v1/premiumIndex',sym),'oi':(base,'/fapi/v1/openInterest',sym),'book':(base,'/fapi/v1/depth',{**sym,'limit':100}),'trades':(base,'/fapi/v1/aggTrades',{**sym,'limit':1000}),'candles':(base,'/fapi/v1/klines',{**sym,'interval':'5m','limit':73}),'oih':(base,'/futures/data/openInterestHist',{**sym,'period':'5m','limit':13}),'spot':(spot,'/api/v3/klines',{**sym,'interval':'5m','limit':73})}
    data,errors=parallel(jobs)
    out={'source':'Binance','quote':'USDT','market_type':'futures','errors':errors,'time':int(time.time())}
    if 'ticker' in data: out.update(price=float(data['ticker']['markPrice']),funding=float(data['ticker']['lastFundingRate'])*100)
    if 'oi' in data: out['oi']=float(data['oi']['openInterest'])
    if 'book' in data: out['book']={'bids':data['book']['bids'],'asks':data['book']['asks']}
    if 'trades' in data: out['trades']=[{'id':str(t['a']),'time':t['T']//1000,'price':float(t['p']),'qty':float(t['q']),'side':'sell' if t['m'] else 'buy'} for t in data['trades']]
    for key in ('candles','spot'):
        if key in data: out[key]=[{'time':int(k[0])//1000,'close':float(k[4]),'volume':float(k[7]),'delta':2*float(k[10])-float(k[7])} for k in data[key] if int(k[6])<time.time()*1000]
    if 'oih' in data: out['oih']=[{'time':int(k['timestamp'])//1000,'oi':float(k['sumOpenInterest'])} for k in data['oih']]
    return out

def parallel(jobs):
    data,errors={},{}
    with ThreadPoolExecutor(max_workers=8) as p:
        futures={k:p.submit(get,*v) for k,v in jobs.items()}
        for k,f in futures.items():
            try: data[k]=f.result()
            except Exception as e: errors[k]=str(e)
    return data,errors

def bybit():
    base='https://api.bybit.com'; sym={'category':'linear','symbol':'BTCUSDT'}
    jobs={'ticker':(base,'/v5/market/tickers',sym),'book':(base,'/v5/market/orderbook',{**sym,'limit':100}),'trades':(base,'/v5/market/recent-trade',{**sym,'limit':1000}),'oih':(base,'/v5/market/open-interest',{**sym,'intervalTime':'5min','limit':13})}
    data,errors=parallel(jobs)
    for k in list(data):
        if data[k].get('retCode')!=0: errors[k]=data.pop(k).get('retMsg','API error')
        else: data[k]=data[k]['result']
    out={'source':'Bybit','quote':'USDT','market_type':'futures','errors':errors,'time':int(time.time())}
    if 'ticker' in data:
        t=data['ticker']['list'][0]; out.update(price=float(t['markPrice']),funding=float(t['fundingRate'])*100,oi=float(t['openInterest']))
    if 'book' in data: out['book']={'bids':data['book']['b'],'asks':data['book']['a']}
    if 'trades' in data: out['trades']=[{'id':str(t['execId']),'time':int(t['time'])//1000,'price':float(t['price']),'qty':float(t['size']),'side':t['side'].lower()} for t in data['trades']['list']]
    if 'oih' in data: out['oih']=sorted([{'time':int(k['timestamp'])//1000,'oi':float(k['openInterest'])} for k in data['oih']['list']],key=lambda x:x['time'])
    return out

def chain():
    base='https://mempool.space/api'; data,errors=parallel({'recent':(base,'/mempool/recent',None),'fees':(base,'/v1/fees/recommended',None),'blocks':(base,'/v1/blocks',None)})
    return {'source':'Mempool','time':int(time.time()),'errors':errors,**data}

def gate():
    base='https://api.gateio.ws/api/v4'; pair={'currency_pair':'BTC_USDT'}
    jobs={'ticker':(base,'/spot/tickers',pair),'book':(base,'/spot/order_book',{**pair,'limit':100}),'trades':(base,'/spot/trades',{**pair,'limit':1000})}
    data,errors=parallel(jobs); out={'source':'Gate','quote':'USDT','market_type':'spot','time':int(time.time()),'errors':errors}
    if data.get('ticker'): out['price']=float(data['ticker'][0]['last'])
    if 'book' in data: out['book']={k:data['book'][k] for k in ('bids','asks')}
    if 'trades' in data: out['trades']=[{'id':str(t['id']),'time':int(float(t['create_time'])),'price':float(t['price']),'qty':float(t['amount']),'side':t['side']} for t in data['trades']]
    return out

def kraken():
    base='https://api.kraken.com/0/public'; pair={'pair':'XBTUSD'}
    data,errors=parallel({'ticker':(base,'/Ticker',pair),'book':(base,'/Depth',{**pair,'count':100}),'trades':(base,'/Trades',{**pair,'count':1000})})
    out={'source':'Kraken','quote':'USD','market_type':'spot','time':int(time.time()),'errors':errors}
    for k,v in data.items():
        try:
            if v['error']: raise ValueError(v['error'])
            r=next(vv for kk,vv in v['result'].items() if kk!='last')
            if k=='ticker': out['price']=float(r['c'][0])
            elif k=='book': out['book']={s:[x[:2] for x in r[s]] for s in ('bids','asks')}
            else: out['trades']=[{'id':str(t[6]) if len(t)>6 else str(t),'time':int(t[2]),'price':float(t[0]),'qty':float(t[1]),'side':'buy' if t[3]=='b' else 'sell'} for t in r]
        except Exception as e: errors[k]=str(e)
    return out

def okx():
    base='https://www.okx.com'; sym={'instId':'BTC-USDT-SWAP'}
    jobs={'ticker':(base,'/api/v5/market/ticker',sym),'mark':(base,'/api/v5/public/mark-price',{**sym,'instType':'SWAP'}),'oi':(base,'/api/v5/public/open-interest',{**sym,'instType':'SWAP'}),'funding':(base,'/api/v5/public/funding-rate',sym),'instrument':(base,'/api/v5/public/instruments',{**sym,'instType':'SWAP'}),'book':(base,'/api/v5/market/books',{**sym,'sz':100}),'trades':(base,'/api/v5/market/trades',{**sym,'limit':500}),'spot_trades':(base,'/api/v5/market/trades',{'instId':'BTC-USDT','limit':500})}
    data,errors=parallel(jobs); out={'source':'OKX','quote':'USDT','market_type':'futures','time':int(time.time()),'errors':errors}
    for k in list(data):
        v=data[k]
        if v.get('code')!='0' or not v.get('data'): errors[k]=v.get('msg') or 'empty response'; del data[k]
        else: data[k]=v['data']
    if 'mark' in data: out['price']=float(data['mark'][0]['markPx'])
    elif 'ticker' in data: out['price']=float(data['ticker'][0]['last'])
    if 'oi' in data: out['oi']=float(data['oi'][0]['oiCcy'])
    if 'funding' in data: out['funding']=float(data['funding'][0]['fundingRate'])*100
    if 'instrument' in data:
        inst=data['instrument'][0]
        if inst['ctValCcy']=='BTC':
            mult=float(inst['ctVal'])*float(inst.get('ctMult') or 1)
            if 'book' in data: out['book']={s:[[x[0],float(x[1])*mult] for x in data['book'][0][s]] for s in ('bids','asks')}
            if 'trades' in data: out['trades']=[{'id':t['tradeId'],'time':int(t['ts'])//1000,'price':float(t['px']),'qty':float(t['sz'])*mult,'side':t['side']} for t in data['trades']]
    if 'spot_trades' in data:
        out['spot_trades'] = [
            {'id':str(t['tradeId']), 'time':int(t['ts'])//1000,
             'price':float(t['px']), 'qty':float(t['sz']), 'side':str(t['side']).lower()}
            for t in data['spot_trades']
        ]
    return out
