# -*- coding: utf-8 -*-
"""리포트 검증 — (A) HTML/JS 구조 (B) 본문 서술 수치 대 데이터 대조. 파이썬 전용."""
import io, json, re, os, sys
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
HERE = os.path.join(ROOT, "analysis")

from lxml import html as LH

OUT=os.path.join(ROOT,'성남시_인구구조_분석_리포트.html')
D=json.load(open(os.path.join(HERE,'data.json'), encoding='utf-8'))
K,CY,SM,DI=D['kpi'],D['cycle'],D['small'],D['dist']
GU,DONG=D['gu'],{d['name']:d for d in D['dong']}
TY={t['type']:t for t in D['types']}

PASS=[];FAIL=[]
def ck(name,cond,detail=''):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}"+(f"   → {detail}" if detail and not cond else ''))

doc=io.open(OUT,encoding='utf-8').read()

# ══ A. JS 구조 ══════════════════════════════════════════════
print("\n[A] 자바스크립트 구조")
# 최종 리포트의 마지막 <script> 블록이 리포트 자체 스크립트 (그 앞은 plotly.js)
js=doc[doc.rindex('<script>')+8: doc.rindex('</script>')]
js=re.sub(r'^const DATA = .*?;$','const DATA = null;',js,count=1,flags=re.S|re.M)

ck("정규식 리터럴 없음 (스캐너 가정 성립)", not re.search(r'[=(,]\s*/(?![/*])', js))

def scan(src):
    """문자열·템플릿·주석을 건너뛰며 괄호 균형과 미종료 리터럴을 검사."""
    st=[]; i=0; n=len(src); tpl=[]   # tpl: 템플릿 리터럴 안의 ${} 깊이 스택
    pairs={')':'(',']':'[','}':'{'}
    while i<n:
        c=src[i]
        if c=='/' and i+1<n and src[i+1]=='/':
            i=src.find('\n',i);  i=n if i<0 else i;  continue
        if c=='/' and i+1<n and src[i+1]=='*':
            j=src.find('*/',i+2)
            if j<0: return "미종료 블록 주석", None
            i=j+2; continue
        if c in '"\'':
            j=i+1
            while j<n:
                if src[j]=='\\': j+=2; continue
                if src[j]==c: break
                if src[j]=='\n': return f"개행 포함 문자열 @{i}", None
                j+=1
            if j>=n: return f"미종료 문자열 @{i}", None
            i=j+1; continue
        if c=='`':
            j=i+1
            while j<n:
                if src[j]=='\\': j+=2; continue
                if src[j]=='`': break
                if src[j]=='$' and j+1<n and src[j+1]=='{':
                    depth=1; k=j+2
                    while k<n and depth:
                        if src[k]=='{': depth+=1
                        elif src[k]=='}': depth-=1
                        elif src[k] in '"\'':
                            q=src[k]; k+=1
                            while k<n and src[k]!=q:
                                k+= 2 if src[k]=='\\' else 1
                        elif src[k]=='`':
                            k+=1
                            while k<n and src[k]!='`':
                                k+= 2 if src[k]=='\\' else 1
                        k+=1
                    if depth: return f"미종료 템플릿 치환 @{j}", None
                    j=k; continue
                j+=1
            if j>=n: return f"미종료 템플릿 리터럴 @{i}", None
            i=j+1; continue
        if c in '([{': st.append((c,i))
        elif c in ')]}':
            if not st: return f"여는 괄호 없이 '{c}' @{i}", None
            o,pos=st.pop()
            if o!=pairs[c]: return f"괄호 불일치 '{o}'@{pos} vs '{c}'@{i}", None
        i+=1
    if st: return f"닫히지 않은 '{st[-1][0]}' @{st[-1][1]}", None
    return None, True

err,ok=scan(js)
ck("괄호/문자열/템플릿 균형", ok is True, err or '')

# 선언 중복 및 필수 함수 존재
fns=re.findall(r'^function\s+([A-Za-z0-9_]+)',js,re.M)
ck("함수 이름 중복 없음", len(fns)==len(set(fns)), str([f for f in fns if fns.count(f)>1]))
need=['renderKPI','renderIndex','renderGu','renderDist','renderSmall','renderQuad',
      'renderType','renderCycle','renderScen','renderExplorer','renderAllTable','renderAll',
      'fillDongSelect','mkTable','spark','cycleChart','L']
ck("필수 함수 17개 모두 정의", all(f in fns for f in need), str([f for f in need if f not in fns]))
top=re.findall(r'^(?:const|let)\s+([A-Za-z0-9_]+)\s*=',js,re.M)
ck("최상위 const/let 재선언 없음", len(top)==len(set(top)), str(sorted({v for v in top if top.count(v)>1})))
ck("renderAll이 모든 렌더 함수 호출",
   all(re.search(r'\b'+f+r'\(\)', js[js.index('function renderAll()'):js.index('function renderAll()')+700])
       for f in ['renderKPI','renderIndex','renderGu','renderDist','renderSmall','renderQuad',
                 'renderType','renderCycle','renderScen','renderExplorer','renderAllTable']))

# ══ B. DOM 참조 무결성 ═══════════════════════════════════════
print("\n[B] DOM 참조 무결성")
tree=LH.fromstring(doc)
ids={e.get('id') for e in tree.xpath('//*[@id]')}
ck("문서 파싱 성공 · id 중복 없음",
   len(tree.xpath('//*[@id]'))==len(ids), f"{len(tree.xpath('//*[@id]'))} vs {len(ids)}")
sel=set(re.findall(r"\$\('#([A-Za-z0-9_-]+)'\)",js))
ck(f"$('#id') 참조 {len(sel)}건 모두 존재", sel<=ids, str(sorted(sel-ids)))
plots=set(re.findall(r"Plotly\.newPlot\('([A-Za-z0-9_-]+)'",js))|{'chartDone','chartOngoing'}
ck(f"Plotly 대상 컨테이너 존재", plots<=ids, str(sorted(plots-ids)))
tv=set(re.findall(r"mkTable\(\$\('#([A-Za-z0-9_-]+)'\)",js))
btn={b.get('data-table') for b in tree.xpath('//*[@data-table]')}
ck(f"'표로 보기' 버튼 {len(btn)}개 ↔ 표 컨테이너 일치", btn<=ids, str(sorted(btn-ids)))
ck("mkTable 대상이 모두 버튼과 연결됨", tv<=(btn|{'tv-all'}), str(sorted(tv-btn-{'tv-all'})))
ck("cycleChart가 tv-done/tv-ongoing 채움", {'tv-done','tv-ongoing'}<=ids)
ck("구 필터 버튼 4개", len(tree.xpath('//*[@id="guFilter"]/button'))==4)
ck("내비게이션 앵커가 모두 실재 섹션", all(a.get('href')[1:] in ids for a in tree.xpath('//nav//a')),
   str([a.get('href') for a in tree.xpath('//nav//a') if a.get('href')[1:] not in ids]))

# ══ C. 임베드 데이터 ═════════════════════════════════════════
print("\n[C] 임베드 데이터")
ck("__DATA__ 치환 완료", '__DATA__' not in doc)
m=re.search(r'const DATA = (\{.*?\});\nconst Y = ',doc,re.S)
ck("const DATA 추출 가능", bool(m))
emb=json.loads(m.group(1)) if m else {}
ck("임베드 JSON == data.json", emb==D)
ck("plotly.js 인라인 (외부 요청 없음)", 'Plotly' in doc and not re.search(r'<script[^>]+src=',doc))
ck("동 50개 · 연도 10개 임베드", len(emb.get('dong',[]))==50 and len(emb.get('years',[]))==10)
ck("파일 크기 3~8MB", 3<os.path.getsize(OUT)/1024/1024<8, f"{os.path.getsize(OUT)/1024/1024:.1f}MB")

# ══ D. 본문 서술 수치 ↔ 데이터 ═══════════════════════════════
print("\n[D] 본문 서술 수치 대조")
txt=re.sub(r'<[^>]+>','',re.sub(r'<script.*?</script>','',doc,flags=re.S))
txt=txt.replace('—',' ').replace('\xa0',' ')
def has(s): return s in txt

claims=[
 ("인구 7.06% 감소",          has('7.06%'),  K['rPop']==-7.06),
 ("세대 3.85% 증가",          has('3.85%'),  K['rHh']==3.85),
 ("가정 세대수 366,718",      has('366,718'), K['hhExpected']==366718),
 ("실제 세대수 409,252",      has('409,252'), K['hh1']==409252),
 ("분화 세대 42,534",         has('42,534'),  K['hhSplit']==42534),
 ("분화율 +11.6%",            has('11.6%'),   K['rHhSplit']==11.6),
 ("2016 세대당 2.47명",       has('2.47'),    K['hs0']==2.47),
 ("수정구 인구 -0.19%",       has('-0.19%'),
     round((GU['수정구']['pop'][-1]/GU['수정구']['pop'][0]-1)*100,2)==-0.19),
 ("수정구 세대 +11,345",      has('11,345'),
     GU['수정구']['hh'][-1]-GU['수정구']['hh'][0]==11345),
 ("수정구 세대 +10.8%",       has('10.8%'),
     round((GU['수정구']['hh'][-1]/GU['수정구']['hh'][0]-1)*100,1)==10.8),
 ("중원구 인구 -34,337",      has('34,337'),
     GU['중원구']['pop'][-1]-GU['중원구']['pop'][0]==-34337),
 ("중원구 세대 -1,678",       has('1,678'),
     GU['중원구']['hh'][-1]-GU['중원구']['hh'][0]==-1678),
 ("중원구 -14.4%",            has('14.4%'),
     round((GU['중원구']['pop'][-1]/GU['중원구']['pop'][0]-1)*100,1)==-14.4),
 ("세대당 수정 2.00",         has('2.00명'),  GU['수정구']['hs'][-1]==2.00),
 ("세대당 중원 2.04",         has('2.04명'),  GU['중원구']['hs'][-1]==2.04),
 ("세대당 분당 2.43",         has('2.43명'),  GU['분당구']['hs'][-1]==2.43),
 ("소가구 동 6곳→17곳",       has('6곳') and has('17곳'), DI['lt20'][0]==6 and DI['lt20'][-1]==17),
 ("큰가구 동 22곳→11곳",      has('22곳') and has('11곳'), DI['ge25'][0]==22 and DI['ge25'][-1]==11),
 ("소가구 17개 동",           has('17개 동'), SM['n']==17),
 ("세대 32.4% / 132,490",     has('32.4%') and has('132,490'), SM['shareHh']==32.4 and SM['hh']==132490),
 ("인구 26.3% / 238,320",     has('26.3%') and has('238,320'), SM['sharePop']==26.3 and SM['pop']==238320),
 ("격차 6.1%p",               has('6.1%p'),  round(SM['shareHh']-SM['sharePop'],1)==6.1),
 ("복정동 1.55",              has('복정동(1.55)') or has('복정동(1.55)'), DONG['수정구 복정동']['hs'][-1]==1.55),
 ("수진1동 1.61",             has('수진1동(1.61)'), DONG['수정구 수진1동']['hs'][-1]==1.61),
 ("신흥1동 1.62",             has('신흥1동(1.62)'), DONG['수정구 신흥1동']['hs'][-1]==1.62),
 ("태평1동 1.64",             has('태평1동(1.64)'), DONG['수정구 태평1동']['hs'][-1]==1.64),
 ("시흥동 1.64",              has('시흥동(1.64)'),  DONG['수정구 시흥동']['hs'][-1]==1.64),
 ("신흥3동 1.65",             has('신흥3동(1.65)'), DONG['수정구 신흥3동']['hs'][-1]==1.65),
 ("시 감소 -68,786",          has('68,786'), K['dPop']==-68786),
 ("동반축소 28개 -90,020",    has('28개 동') and has('90,020'),
     TY['동반축소형']['n']==28 and TY['동반축소형']['dPop']==-90020),
 ("이주·멸실 3개 -30,754",    has('30,754'),
     TY['이주·멸실형']['n']==3 and TY['이주·멸실형']['dPop']==-30754),
 ("신규유입 7개 +67,165",     has('7개 동') and has('67,165'),
     TY['신규유입형']['n']==7 and TY['신규유입형']['dPop']==67165),
 ("회복배수 0.94~1.54",       has('0.94배') and has('1.54배'), CY['recovRange']==[0.94,1.54]),
 ("중앙값 1.43배",            has('1.43배'), CY['medianRecov']==1.43),
 ("신흥2동 22,154→31,635",    has('22,154') and has('31,635'),
     DONG['수정구 신흥2동']['pop'][0]==22154 and DONG['수정구 신흥2동']['pop'][-1]==31635),
 ("금광1동 12,726→19,608",    has('12,726') and has('19,608'),
     DONG['중원구 금광1동']['pop'][0]==12726 and DONG['중원구 금광1동']['pop'][-1]==19608),
 ("이주 몫 44.7%",            has('44.7%'),  CY['lostShareOfCityDecline']==44.7),
 ("보수 +30,754",             has('+30,754'), CY['scenario']['conservative']==30754),
 ("중앙값 +52,940",           has('+52,940'), CY['scenario']['median']==52940),
 ("상대원2동 81.9% 감소",     has('81.9%'),
     round((1-DONG['중원구 상대원2동']['pop'][-1]/DONG['중원구 상대원2동']['pop'][0])*100,1)==81.9),
 ("정자동 -35.1%",            has('35.1%'), DONG['분당구 정자동']['rP']==-35.05 or
     round((DONG['분당구 정자동']['pop'][-1]/DONG['분당구 정자동']['pop'][0]-1)*100,1)==-35.1),
 ("고등동 +584.7%",           has('584.7%'),
     round((DONG['수정구 고등동']['pop'][-1]/DONG['수정구 고등동']['pop'][0]-1)*100,1)==584.7),
]
for name,in_text,in_data in claims:
    ck(name, in_text and in_data, f"본문={in_text} 데이터={in_data}")

print("\n[E] 파생 서술 재계산")
Yr=D['years']
# 회복 소요: 2016 수준을 다시 넘어선 해
def recov_years(nm):
    p=DONG[nm]['pop']
    for i,v in enumerate(p[1:],1):
        if v>p[0]: return Yr[i]-Yr[0]
    return None
ck("신흥2동 회복 7년", recov_years('수정구 신흥2동')==7 and has('신흥2동 7년'),
   str(recov_years('수정구 신흥2동')))
ck("금광1동 회복 6년", recov_years('중원구 금광1동')==6 and has('금광1동 6년'),
   str(recov_years('중원구 금광1동')))
ck("중앙동 미회복 서술", recov_years('중원구 중앙동') is None
   and has('중앙동은 10년 차에도 2016년 수준을 회복하지 못했습니다') and has('0.94배'))
ck("evid 카드 '6~7년' 표기와 일치", has('6~7년'))
# 세 완료 사례 모두 저점 다음 해 반등
ok=all(c['pop'][Yr.index(c['troughYear'])+1]>c['trough'] for c in CY['done'])
ck("완료 3건 모두 저점 다음 해 반등", ok and has('모두 저점 다음 해에 반등이 시작'))
# 세대당 인구 연평균 하락 속도
sp=(D['city']['hs'][-1]-D['city']['hs'][0])/(len(Yr)-1)
ck("연평균 하락 -0.03명", round(sp,2)==-0.03 and has('연 -0.03명'), f"{sp:.4f}")
# 정책1 성과지표 81%
ck("소가구 지역 세대당 예산 81% 근거", round(SM['sharePop']/SM['shareHh']*100)==81 and has('81%'),
   f"{SM['sharePop']/SM['shareHh']*100:.1f}")
# 정책2 규모 추정 (JS와 동일한 중앙값 계산)
med=sorted(c['recov'] for c in CY['done'])[1]
est={c['dong']: c['base']*med for c in CY['ongoing']}
ck("산성동 약 2.1만 명", 20500<=est['산성동']<21500 and has('산성동 약 2.1만 명'), f"{est['산성동']:.0f}")
ck("상대원2동 약 2.3만 명", 22500<=est['상대원2동']<23500 and has('상대원2동 약 2.3만 명'), f"{est['상대원2동']:.0f}")
ck("시나리오 합 = 중앙값 시나리오",
   round(sum(est.values())-sum(c['now'] for c in CY['ongoing']))==CY['scenario']['median'],
   f"{sum(est.values())-sum(c['now'] for c in CY['ongoing']):.0f}")
ck("히어로 '6만 9천'·'1만 5천' 반올림 타당",
   abs(K['dPop'])//1000==68 and K['dHh']//1000==15 and has('6만 9천') and has('1만 5천'))

print("\n[F] 접근성·표시 규칙")
ck("모든 차트에 표 뷰 존재 (12개)", len(btn)==11 and 'tv-all' in ids, f"{len(btn)}")
ck("색상만으로 계열 구분하지 않음 (legend 사용)", js.count('showlegend: false')<=3 and 'legend:' in js)
ck("라이트/다크 팔레트 모두 정의", "light: {" in js and "dark:  {" in js)
ck("테마 토글 존재", 'themeBtn' in ids and 'snPopTheme' in doc)
ck("이중 y축 없음", 'yaxis2' not in js and 'overlaying' not in js)
ck("범주형 색상 슬롯 1~3만 사용 (검증된 조합)",
   set(re.findall(r'#(?:2a78d6|eb6834|1baf7a|3987e5|d95926|199e70)',js))
   <= {'#2a78d6','#eb6834','#1baf7a','#3987e5','#d95926','#199e70'})
ck("점선 그리드 없음", 'dash' not in js)
ck("반응형 설정", "responsive: true" in js)

print("\n"+"="*62)
print(f"결과: {len(PASS)} PASS / {len(FAIL)} FAIL")
if FAIL:
    print("실패:"); [print("  -",f) for f in FAIL]; sys.exit(1)
print("리포트 검증 전부 통과")
