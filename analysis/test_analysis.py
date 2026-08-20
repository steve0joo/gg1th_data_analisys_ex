# -*- coding: utf-8 -*-
"""분석 정확성 검증 — 원본 CSV를 pandas 없이 독립 재파싱하여 교차 검증."""
import csv, json, re, io, math, sys
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
HERE = os.path.join(ROOT, "analysis")


CSV='population_data/201612_202512_주민등록인구및세대현황_연간.csv'
JSON=os.path.join(HERE,'data.json')
YEARS=list(range(2016,2026))

PASS=[]; FAIL=[]
def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {detail}" if detail and not cond else ''))

# ── 독립 재파싱: csv 모듈 + 수동 숫자 변환 (pandas thousands= 에 의존하지 않음) ──
with io.open(CSV, encoding='cp949', newline='') as f:
    raw=list(csv.reader(f))
header, body = raw[0], raw[1:]
def num(s):
    s=s.strip().replace(',','')
    return float(s) if '.' in s else int(s)
col={h:i for i,h in enumerate(header)}
R=[]
for row in body:
    name=row[0]
    parts=[x for x in re.sub(r'\s*\(\d+\)\s*$','',name).strip().split() if x!='경기도']
    lvl='시' if len(parts)==1 else '구' if len(parts)==2 else '동'
    rec=dict(level=lvl, gu=(parts[1] if len(parts)>=2 else None),
             dong=(parts[2] if len(parts)>=3 else None), raw=name)
    for y in YEARS:
        for k,short in [('총인구수','pop'),('세대수','hh'),('세대당 인구','hs'),
                        ('남자 인구수','m'),('여자 인구수','f'),('남여 비율','sr')]:
            rec[f'{short}{y}']=num(row[col[f'{y}년_{k}']])
    R.append(rec)

CITY=[r for r in R if r['level']=='시']
GU  =[r for r in R if r['level']=='구']
DONG=[r for r in R if r['level']=='동']

print("\n[1] 원본 데이터 무결성")
check("행 수 = 54 (시1 + 구3 + 동50)", len(R)==54 and len(CITY)==1 and len(GU)==3 and len(DONG)==50,
      f"got {len(R)}/{len(CITY)}/{len(GU)}/{len(DONG)}")
check("열 수 = 61 (행정구역 + 10년 x 6지표)", len(header)==61, f"got {len(header)}")
check("빈 셀 없음", all(c.strip()!='' for row in body for c in row))
check("모든 인구/세대 값 > 0", all(r[f'{k}{y}']>0 for r in R for y in YEARS for k in ('pop','hh','m','f')))
check("동 이름 중복 없음", len({(r['gu'],r['dong']) for r in DONG})==50)

print("\n[2] 원본 내부 항등식")
bad=[(r['raw'],y) for r in R for y in YEARS if r[f'm{y}']+r[f'f{y}']!=r[f'pop{y}']]
check("남자+여자 == 총인구 (540건)", not bad, f"{len(bad)}건 불일치 예: {bad[:3]}")
tol=[(r['raw'],y,r[f'hs{y}'],round(r[f'pop{y}']/r[f'hh{y}'],2)) for r in R for y in YEARS
     if abs(r[f'hs{y}']-r[f'pop{y}']/r[f'hh{y}'])>0.005+1e-9]
check("세대당인구 == 총인구/세대수 (±0.005)", not tol, f"{len(tol)}건 예: {tol[:3]}")
sr=[(r['raw'],y) for r in R for y in YEARS if abs(r[f'sr{y}']-r[f'm{y}']/r[f'f{y}'])>0.005+1e-9]
check("남여비율 == 남자/여자 (±0.005)", not sr, f"{len(sr)}건 예: {sr[:3]}")

print("\n[3] 계층 합계 정합성")
city=CITY[0]
for k,label in [('pop','총인구'),('hh','세대수'),('m','남자'),('f','여자')]:
    diffs=[(y, sum(g[f'{k}{y}'] for g in GU), city[f'{k}{y}']) for y in YEARS
           if sum(g[f'{k}{y}'] for g in GU)!=city[f'{k}{y}']]
    check(f"구3개 합 == 시 [{label}] (10년)", not diffs, f"{diffs[:3]}")
for g in GU:
    ds=[d for d in DONG if d['gu']==g['gu']]
    diffs=[(y, sum(d[f'pop{y}'] for d in ds), g[f'pop{y}']) for y in YEARS
           if sum(d[f'pop{y}'] for d in ds)!=g[f'pop{y}']]
    check(f"{g['gu']} 동 합 == 구 [총인구] (동 {len(ds)}개)", not diffs, f"{diffs[:3]}")
    diffs=[(y, sum(d[f'hh{y}'] for d in ds), g[f'hh{y}']) for y in YEARS
           if sum(d[f'hh{y}'] for d in ds)!=g[f'hh{y}']]
    check(f"{g['gu']} 동 합 == 구 [세대수] (동 {len(ds)}개)", not diffs, f"{diffs[:3]}")

print("\n[4] JSON 산출물 <-> 원본 대조")
J=json.load(open(JSON))
check("years 일치", J['years']==YEARS)
check("city.pop 일치", J['city']['pop']==[city[f'pop{y}'] for y in YEARS])
check("city.hh 일치",  J['city']['hh']==[city[f'hh{y}'] for y in YEARS])
check("city.hs 일치",  J['city']['hs']==[city[f'hs{y}'] for y in YEARS])
check("city 남+여 == city.pop", [a+b for a,b in zip(J['city']['male'],J['city']['female'])]==J['city']['pop'])
check("gu 3개 키 일치", set(J['gu'])=={g['gu'] for g in GU})
gu_ok=all(J['gu'][g['gu']]['pop']==[g[f'pop{y}'] for y in YEARS] and
          J['gu'][g['gu']]['hh'] ==[g[f'hh{y}'] for y in YEARS] for g in GU)
check("gu.pop/hh 전량 일치", gu_ok)
idx={(d['gu'],d['dong']):d for d in DONG}
dong_ok=all(j['pop']==[idx[(j['gu'],j['dong'])][f'pop{y}'] for y in YEARS] and
            j['hh'] ==[idx[(j['gu'],j['dong'])][f'hh{y}']  for y in YEARS] and
            j['hs'] ==[idx[(j['gu'],j['dong'])][f'hs{y}']  for y in YEARS]
            for j in J['dong'])
check("dong 50개 pop/hh/hs 전량 일치", dong_ok and len(J['dong'])==50)
check("JSON 동 합 == JSON 시 (2025)", sum(d['pop'][-1] for d in J['dong'])==J['city']['pop'][-1])

print("\n[5] KPI 재계산")
K=J['kpi']
p0,p1=city['pop2016'],city['pop2025']; h0,h1=city['hh2016'],city['hh2025']
check("pop0/pop1", (K['pop0'],K['pop1'])==(p0,p1), f"{K['pop0']},{K['pop1']} vs {p0},{p1}")
check("dPop = pop1-pop0 = -68,786", K['dPop']==p1-p0==-68786, f"{K['dPop']}")
check("rPop = -7.06%", K['rPop']==round((p1/p0-1)*100,2)==-7.06, f"{K['rPop']}")
check("dHh = +15,165", K['dHh']==h1-h0==15165, f"{K['dHh']}")
check("rHh = +3.85%", K['rHh']==round((h1/h0-1)*100,2)==3.85, f"{K['rHh']}")
check("dHs = -0.26", abs(K['dHs']-(city['hs2025']-city['hs2016']))<1e-9 and K['dHs']==-0.26, f"{K['dHs']}")
hexp=p1/city['hs2016']
check("hhExpected = 2025인구/2016세대당인구", K['hhExpected']==int(round(hexp)), f"{K['hhExpected']} vs {hexp:.1f}")
check("hhSplit = 실제세대 - 예상세대 = +42,534", K['hhSplit']==int(round(h1-hexp))==42534, f"{K['hhSplit']}")
check("여초격차 2016 +7,832 / 2025 +11,034",
      K['femGap0']==city['f2016']-city['m2016']==7832 and K['femGap1']==city['f2025']-city['m2025']==11034)
check("인구는 감소, 세대는 증가 (방향 반대)", K['dPop']<0 and K['dHh']>0)
check("세대당인구 10년 연속 단조 감소",
      all(city[f'hs{a}']>=city[f'hs{b}'] for a,b in zip(YEARS,YEARS[1:])))

print("\n[6] 유형 분류 검증")
def classify(rP,rH):
    if rP>5 and rH>5: return '신규유입형'
    if rP<-15 and rH<-15: return '이주·멸실형'
    if rP<0 and rH>=0: return '가구분화형'
    if rP<0 and rH<0: return '동반축소형'
    return '안정형'
recl={}
for d in DONG:
    rP=(d['pop2025']/d['pop2016']-1)*100; rH=(d['hh2025']/d['hh2016']-1)*100
    recl[(d['gu'],d['dong'])]=classify(rP,rH)
check("JSON 유형 == 독립 재분류 (50개 동)",
      all(j['type']==recl[(j['gu'],j['dong'])] for j in J['dong']),
      str([(j['name'],j['type'],recl[(j['gu'],j['dong'])]) for j in J['dong']
           if j['type']!=recl[(j['gu'],j['dong'])]][:3]))
tsum={t['type']:t for t in J['types']}
check("유형별 동수 합 = 50", sum(t['n'] for t in J['types'])==50)
check("유형별 인구증감 합 = 시 전체 증감 (-68,786)",
      sum(t['dPop'] for t in J['types'])==K['dPop'], f"{sum(t['dPop'] for t in J['types'])}")
check("유형별 세대증감 합 = 시 전체 증감 (+15,165)",
      sum(t['dHh'] for t in J['types'])==K['dHh'], f"{sum(t['dHh'] for t in J['types'])}")
check("유형별 2025인구 합 = 시 2025 인구",
      sum(t['pop2025'] for t in J['types'])==p1)
check("각 유형 분류 규칙 자기일치", all(
      (t=='신규유입형' and j['rP']>5 and j['rH']>5) or
      (t=='이주·멸실형' and j['rP']<-15 and j['rH']<-15) or
      (t=='가구분화형' and j['rP']<0 and j['rH']>=0) or
      (t=='동반축소형' and j['rP']<0 and j['rH']<0) or
      (t=='안정형')
      for j in J['dong'] for t in [j['type']]))

print("\n[7] 재개발 사이클 검증")
C=J['cycle']
for c in C['done']+C['ongoing']:
    src=idx[(c['gu'],c['dong'])]
    ok = (c['pop']==[src[f'pop{y}'] for y in YEARS]
          and c['base']==src['pop2016'] and c['now']==src['pop2025']
          and c['trough']==min(c['pop']) and c['troughYear']==YEARS[c['pop'].index(min(c['pop']))]
          and abs(c['recov']-c['now']/c['base'])<5e-4)
    check(f"{c['name']} 궤적/저점/회복배수", ok,
          f"trough={c['trough']}@{c['troughYear']} recov={c['recov']}")
check("완료 3개동은 저점 이후 반등 (현재 > 저점)",
      all(c['now']>c['trough'] for c in C['done']))
check("진행 3개동은 2025가 저점 (반등 미확인)",
      all(c['troughYear']==2025 for c in C['ongoing']))
lost=sum(c['base']-c['now'] for c in C['ongoing'])
check("진행 3개동 이탈 인구 = 30,754", C['lost']==lost==30754, f"{C['lost']}")
check("이탈 인구/시 전체 감소 = 44.7%",
      C['lostShareOfCityDecline']==round(lost/abs(K['dPop'])*100,1)==44.7)
med=sorted(c['recov'] for c in C['done'])[1]
check("회복배수 중앙값 1.43", C['medianRecov']==round(med,2)==1.43, f"{C['medianRecov']}")
check("보수 시나리오 = 이탈분 원상회복 = +30,754", C['scenario']['conservative']==lost==30754)
check("중립 시나리오 = base*1.43 - 현재 = +52,940",
      C['scenario']['median']==int(round(sum(c['base']*med for c in C['ongoing'])
                                         -sum(c['now'] for c in C['ongoing'])))==52940,
      f"{C['scenario']['median']}")
check("중립 > 보수 시나리오", C['scenario']['median']>C['scenario']['conservative'])

print("\n[8] 소가구(세대당인구<2.0) 집계 검증")
S=J['small']
sm=[d for d in DONG if d['hs2025']<2.0]
check("해당 동 수 = 17", S['n']==len(sm)==17, f"{S['n']} vs {len(sm)}")
check("세대 합 = 132,490", S['hh']==sum(d['hh2025'] for d in sm)==132490, f"{S['hh']}")
check("인구 합 = 238,320", S['pop']==sum(d['pop2025'] for d in sm)==238320, f"{S['pop']}")
check("세대 점유율 = 32.4%", S['shareHh']==round(sum(d['hh2025'] for d in sm)/h1*100,1)==32.4)
check("인구 점유율 = 26.3%", S['sharePop']==round(sum(d['pop2025'] for d in sm)/p1*100,1)==26.3)
check("세대 점유율 > 인구 점유율 (소가구 특성)", S['shareHh']>S['sharePop'])
check("리스트 오름차순 정렬(세대당인구)",
      all(a['hs']<=b['hs'] for a,b in zip(S['list'],S['list'][1:])))
check("리스트 전원 hs<2.0", all(x['hs']<2.0 for x in S['list']) and len(S['list'])==17)

print("\n[9] 분포 추이 검증")
D_=J['dist']
for i,y in enumerate(YEARS):
    lt=sum(1 for d in DONG if d[f'hs{y}']<2.0)
    mid=sum(1 for d in DONG if 2.0<=d[f'hs{y}']<2.5)
    ge=sum(1 for d in DONG if d[f'hs{y}']>=2.5)
    if (D_['lt20'][i],D_['mid'][i],D_['ge25'][i])!=(lt,mid,ge):
        FAIL.append(f"dist {y}"); print(f"  FAIL  dist {y}: {D_['lt20'][i]},{D_['mid'][i]},{D_['ge25'][i]} vs {lt},{mid},{ge}")
        break
else:
    check("연도별 3구간 동 수 전량 일치", True)
check("3구간 합 = 50 (모든 연도)",
      all(a+b+c==50 for a,b,c in zip(D_['lt20'],D_['mid'],D_['ge25'])))
check("<2.0 동 수 증가 6 -> 17", D_['lt20'][0]==6 and D_['lt20'][-1]==17)
check(">=2.5 동 수 감소 22 -> 11", D_['ge25'][0]==22 and D_['ge25'][-1]==11)

print("\n[10] 리포트 인용 수치 스팟체크")
spot=[("성남시 2016 총인구", city['pop2016'], 974580),
      ("성남시 2025 총인구", city['pop2025'], 905794),
      ("성남시 2025 세대수", city['hh2025'], 409252),
      ("수정구 2025 세대당인구", [g for g in GU if g['gu']=='수정구'][0]['hs2025'], 2.00),
      ("중원구 2016->2025 인구증감",
       [g for g in GU if g['gu']=='중원구'][0]['pop2025']-[g for g in GU if g['gu']=='중원구'][0]['pop2016'], -34337),
      ("분당구 2025 세대당인구", [g for g in GU if g['gu']=='분당구'][0]['hs2025'], 2.43),
      ("복정동 2025 세대당인구", idx[('수정구','복정동')]['hs2025'], 1.55),
      ("고등동 인구 2016->2025", (idx[('수정구','고등동')]['pop2016'], idx[('수정구','고등동')]['pop2025']), (1723,11797)),
      ("위례동 2025 인구", idx[('수정구','위례동')]['pop2025'], 45473),
      ("상대원2동 2025 인구", idx[('중원구','상대원2동')]['pop2025'], 2911)]
for label,got,exp in spot:
    check(f"{label} = {exp}", got==exp, f"got {got}")

print("\n" + "="*60)
print(f"결과: {len(PASS)} PASS / {len(FAIL)} FAIL")
if FAIL:
    print("실패 항목:"); [print("  -",f) for f in FAIL]
    sys.exit(1)
print("모든 검증 통과")
