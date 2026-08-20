import pandas as pd, re, json, numpy as np
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
HERE = os.path.join(ROOT, "analysis")

YEARS=list(range(2016,2026))
df = pd.read_csv('population_data/201612_202512_주민등록인구및세대현황_연간.csv', encoding='cp949', thousands=',')
rows=[]
for s in df['행정구역']:
    p=[x for x in re.sub(r'\s*\(\d+\)\s*$','',s).strip().split() if x!='경기도']
    rows.append(('시','성남시',None) if len(p)==1 else ('구',p[1],None) if len(p)==2 else ('동',p[1],p[2]))
df=pd.concat([pd.DataFrame(rows,columns=['level','구','동']), df.drop(columns=['행정구역'])],axis=1)

def series(r,key): return [int(r[f'{y}년_{key}']) for y in YEARS]
def fseries(r,key): return [float(r[f'{y}년_{key}']) for y in YEARS]

city=df[df.level=='시'].iloc[0]
C=dict(pop=series(city,'총인구수'), hh=series(city,'세대수'),
       hs=fseries(city,'세대당 인구'), male=series(city,'남자 인구수'), female=series(city,'여자 인구수'))

GU={}
for _,r in df[df.level=='구'].iterrows():
    GU[r['구']]=dict(pop=series(r,'총인구수'), hh=series(r,'세대수'), hs=fseries(r,'세대당 인구'),
                     male=series(r,'남자 인구수'), female=series(r,'여자 인구수'))

D=[]
for _,r in df[df.level=='동'].iterrows():
    pop=series(r,'총인구수'); hh=series(r,'세대수'); hs=fseries(r,'세대당 인구')
    rP=(pop[-1]/pop[0]-1)*100; rH=(hh[-1]/hh[0]-1)*100
    if   rP>5 and rH>5:        t='신규유입형'
    elif rP<-15 and rH<-15:    t='이주·멸실형'
    elif rP<0 and rH>=0:       t='가구분화형'
    elif rP<0 and rH<0:        t='동반축소형'
    else:                      t='안정형'
    D.append(dict(gu=r['구'], dong=r['동'], name=f"{r['구']} {r['동']}",
                  pop=pop, hh=hh, hs=hs, male=series(r,'남자 인구수'), female=series(r,'여자 인구수'),
                  dP=pop[-1]-pop[0], dH=hh[-1]-hh[0], rP=round(rP,2), rH=round(rH,2),
                  dHs=round(hs[-1]-hs[0],2), type=t,
                  sex=round(r['2025년_남자 인구수']/r['2025년_여자 인구수'],3)))

# ── 파생 지표 ──
p0,p1=C['pop'][0],C['pop'][-1]; h0,h1=C['hh'][0],C['hh'][-1]
h_exp = p1/C['hs'][0]
K=dict(
  pop0=p0, pop1=p1, dPop=p1-p0, rPop=round((p1/p0-1)*100,2),
  hh0=h0, hh1=h1, dHh=h1-h0, rHh=round((h1/h0-1)*100,2),
  hs0=C['hs'][0], hs1=C['hs'][-1], dHs=round(C['hs'][-1]-C['hs'][0],2),
  rHs=round((C['hs'][-1]/C['hs'][0]-1)*100,2),
  hhExpected=int(round(h_exp)), hhSplit=int(round(h1-h_exp)),
  rHhSplit=round((h1/h_exp-1)*100,1),
  femGap0=C['female'][0]-C['male'][0], femGap1=C['female'][-1]-C['male'][-1],
)

# 유형별 집계
tp=pd.DataFrame(D)
agg=tp.groupby('type').agg(n=('dong','count'), dPop=('dP','sum'), dHh=('dH','sum'),
                           pop2016=('pop',lambda s: sum(x[0] for x in s)),
                           pop2025=('pop',lambda s: sum(x[-1] for x in s))).reset_index()
TYPES=agg.to_dict('records')

# 세대당 인구 분포 추이
hs_all=np.array([d['hs'] for d in D])
DIST=dict(
  lt20=[int((hs_all[:,i]<2.0).sum()) for i in range(10)],
  ge25=[int((hs_all[:,i]>=2.5).sum()) for i in range(10)],
  mid=[int(((hs_all[:,i]>=2.0)&(hs_all[:,i]<2.5)).sum()) for i in range(10)],
  mean=[round(float(hs_all[:,i].mean()),2) for i in range(10)],
)

# 소가구 밀집(2025 세대당 인구 < 2.0)
small=[d for d in D if d['hs'][-1]<2.0]
small_sorted=sorted(small, key=lambda d:d['hs'][-1])
SMALL=dict(n=len(small), hh=sum(d['hh'][-1] for d in small), pop=sum(d['pop'][-1] for d in small),
           shareHh=round(sum(d['hh'][-1] for d in small)/h1*100,1),
           sharePop=round(sum(d['pop'][-1] for d in small)/p1*100,1),
           list=[dict(name=d['name'],gu=d['gu'],dong=d['dong'],hs=d['hs'][-1],hs0=d['hs'][0],
                      hh=d['hh'][-1],pop=d['pop'][-1],rP=d['rP']) for d in small_sorted])

# 재개발 사이클
def find(n): return next(d for d in D if d['name']==n)
DONE=['수정구 신흥2동','중원구 금광1동','중원구 중앙동']
ONGOING=['수정구 산성동','중원구 상대원2동','분당구 정자동']
def cyc(n):
    d=find(n); pop=d['pop']; base=pop[0]; lo=int(np.argmin(pop))
    return dict(name=n, gu=d['gu'], dong=d['dong'], pop=pop, hh=d['hh'],
                base=base, trough=pop[lo], troughYear=YEARS[lo], now=pop[-1],
                recov=round(pop[-1]/base,3), lossPct=round((pop[lo]/base-1)*100,1),
                yearsSinceTrough=YEARS[-1]-YEARS[lo])
CYCLE=dict(done=[cyc(n) for n in DONE], ongoing=[cyc(n) for n in ONGOING])
med=float(np.median([c['recov'] for c in CYCLE['done']]))
CYCLE['medianRecov']=round(med,2)
CYCLE['recovRange']=[round(min(c['recov'] for c in CYCLE['done']),2),
                     round(max(c['recov'] for c in CYCLE['done']),2)]
lost=sum(c['base']-c['now'] for c in CYCLE['ongoing'])
CYCLE['lost']=int(lost)
CYCLE['lostShareOfCityDecline']=round(lost/abs(K['dPop'])*100,1)
# 시나리오
cons=sum(c['base'] for c in CYCLE['ongoing'])-sum(c['now'] for c in CYCLE['ongoing'])
mid_=sum(c['base']*med for c in CYCLE['ongoing'])-sum(c['now'] for c in CYCLE['ongoing'])
CYCLE['scenario']=dict(conservative=int(round(cons)), median=int(round(mid_)))

OUT=dict(years=YEARS, city=C, gu=GU, dong=D, kpi=K, types=TYPES, dist=DIST,
         small=SMALL, cycle=CYCLE)
p=os.path.join(HERE,'data.json')
json.dump(OUT, open(p,'w'), ensure_ascii=False)
print("written", p)
print(json.dumps(K, ensure_ascii=False, indent=1))
print("\nTYPES:"); [print(t) for t in TYPES]
print("\nSMALL:", {k:v for k,v in SMALL.items() if k!='list'})
print("\nCYCLE done:"); [print(c) for c in CYCLE['done']]
print("CYCLE ongoing:"); [print(c) for c in CYCLE['ongoing']]
print("median recov", CYCLE['medianRecov'], "range", CYCLE['recovRange'])
print("lost", CYCLE['lost'], "share", CYCLE['lostShareOfCityDecline'],"%")
print("scenario", CYCLE['scenario'])
print("\nDIST:", DIST)
