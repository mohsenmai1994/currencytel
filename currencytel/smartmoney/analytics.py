import math

def analyze(m,threshold=100000):
    trades=sorted(m.get('trades',[]),key=lambda t:t['time']); end=m['time']; recent=[t for t in trades if end-900<=t['time']<=end+10]; large=[{**t,'value':t['qty']*t['price']} for t in recent if t['qty']*t['price']>=threshold]
    buy=sum(t['value'] for t in large if t['side']=='buy'); sell=sum(t['value'] for t in large if t['side']=='sell'); total=buy+sell
    book=m.get('book'); imbalance=None; levels=[]
    if book and book['bids'] and book['asks']:
        mid=(float(book['bids'][0][0])+float(book['asks'][0][0]))/2
        b=sum(float(p)*float(q) for p,q in book['bids'] if abs(float(p)/mid-1)<=.005); a=sum(float(p)*float(q) for p,q in book['asks'] if abs(float(p)/mid-1)<=.005)
        if b+a: imbalance=(b-a)/(b+a)
        for side in ('bids','asks'):
            levels.extend({'side':side,'price':float(p),'value':float(p)*float(q)} for p,q in book[side] if abs(float(p)/mid-1)<=.005)
    candles=m.get('candles',[]); spot=m.get('spot',[]); cvd=[]; acc=0
    for k in candles:
        acc+=k['delta']; cvd.append({'time':k['time'],'value':acc,'price':k['close']})
    window=candles[-12:]; sw=spot[-12:]; volume=sum(k['volume'] for k in window); delta=sum(k['delta'] for k in window); sv=sum(k['volume'] for k in sw)
    flow=delta/volume if volume and len(window)==12 else None; sf=sum(k['delta'] for k in sw)/sv if sv and len(sw)==12 else None
    pc=(window[-1]['close']/window[0]['close']-1)*100 if len(window)==12 else None
    oi=m.get('oih',[]); oc=(oi[-1]['oi']/oi[0]['oi']-1)*100 if len(oi)>=12 and oi[0]['oi'] else None
    components={'futures_flow':(flow,40),'spot_flow':(sf,30),'large_trade':((buy-sell)/total if total and len(large)>=3 else None,20),'orderbook':(imbalance,10)}
    weight=sum(w for v,w in components.values() if v is not None)
    score=round(50+50*sum(v*w for v,w in components.values() if v is not None)/weight) if weight>=50 and (flow is not None or sf is not None) else None
    state='نامشخص'
    if score is not None: state='فشار خرید' if score>=60 else 'فشار فروش' if score<=40 else 'متعادل'
    alerts=[]
    if pc is not None and flow is not None:
        if pc>.2 and flow<-.05: alerts.append('واگرایی نزولی قیمت و CVD؛ نیازمند تأیید')
        if pc<-.2 and flow>.05: alerts.append('واگرایی صعودی قیمت و CVD؛ نیازمند تأیید')
        if sf is not None and abs(pc)<.5 and sf>.08 and flow>.05: alerts.append('انباشت احتمالی: خرید تهاجمی همسو در بازار نقدی و مشتقه')
        if sf is not None and abs(pc)<.5 and sf<-.08 and flow<-.05: alerts.append('توزیع احتمالی: فروش تهاجمی همسو در بازار نقدی و مشتقه')
    if oc is not None and pc is not None and abs(pc)>.2 and abs(oc)>.5: alerts.append(('افزایش' if oc>0 else 'کاهش')+' موقعیت‌های باز همراه با '+('رشد' if pc>0 else 'افت')+' قیمت؛ جهت موقعیت‌ها قطعی نیست')
    return {'score':score,'coverage':weight,'state':state,'buy':buy if 'trades' in m else None,'sell':sell if 'trades' in m else None,'large':sorted(large,key=lambda t:t['time'],reverse=True)[:60],'sample_seconds':max(0,end-min(t['time'] for t in recent)) if recent else None,'sample_count':len(recent),'cvd':cvd,'flow':flow,'spot_flow':sf,'imbalance':imbalance,'oi_change':oc,'price_change':pc,'levels':sorted(levels,key=lambda l:l['value'],reverse=True)[:20],'alerts':alerts,'components':{k:v for k,(v,w) in components.items()}}
