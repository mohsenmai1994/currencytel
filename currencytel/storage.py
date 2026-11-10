"""Atomic, schema-versioned snapshots served by GitHub Pages."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json, os, hashlib
from .catalog import SOCIAL
from .models import MarketQuote
from .report import render_report

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'

def read_json(path,default):
    try: return json.loads(Path(path).read_text(encoding='utf-8'))
    except (FileNotFoundError,json.JSONDecodeError):return default

def write_atomic(path,obj):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(temp,path)

def write_text_atomic(path,text):
    path=Path(path)
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(text,encoding='utf-8')
    os.replace(temp,path)

def fingerprint(quotes):
    compact=render_report(quotes,footer=False)
    return hashlib.sha256(compact.encode('utf-8')).hexdigest()

def save_market(quotes:dict[str,MarketQuote],max_history=336):
    stamp=datetime.now(ZoneInfo('Asia/Tehran')).isoformat(timespec='seconds')
    ordered=[q for a in SOCIAL if (q:=quotes.get(a.key))]
    extras=sorted((v for k,v in quotes.items() if k not in {a.key for a in SOCIAL}),
                  key=lambda item:(item.asset.category,item.asset.label))
    market={
        'schema_version':2,'fetched_at':stamp,'timezone':'Asia/Tehran',
        'source':'https://alanchand.com/en','source_label':'الان چند',
        'complete':len(ordered)==len(SOCIAL), 'social_count':len(ordered),
        'extra_count':len(extras),'channel':'currencytel','bot':'currencytel_bot',
        'items':[q.to_dict() for q in ordered+extras]
    }
    # History only records successful complete snapshots; no fictional data.
    prior=read_json(DATA/'history.json',{'schema_version':1,'points':[]})
    values={k:str(item.value) for k,item in quotes.items()}
    points=[p for p in prior.get('points',[]) if isinstance(p,dict)]
    # Deduplicate repeated workflow invocations at the same minute.
    if points and points[-1].get('values')==values:
        pass
    else:
        points.append({'at':stamp,'values':values})
    write_atomic(DATA/'history.json',{'schema_version':1,'points':points[-max_history:]})
    write_atomic(DATA/'market.json',market)
    report=render_report(quotes)
    write_text_atomic(ROOT/'market_log.txt',report+'\n')
    return market,report,fingerprint(quotes)
