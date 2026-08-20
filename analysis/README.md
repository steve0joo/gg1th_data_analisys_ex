# 성남시 인구구조 분석 파이프라인

`population_data/201612_202512_주민등록인구및세대현황_연간.csv` (행정안전부 주민등록 인구통계,
성남시 3개 구 50개 행정동 × 10년 × 6개 지표) 를 분석해 자체 완결형 인터랙티브 HTML 리포트를 만듭니다.

## 실행

```bash
python3 analysis/build_data.py     # 원본 CSV → analysis/data.json (파생 지표 계산)
python3 analysis/build_report.py   # data.json + parts/ → 성남시_인구구조_분석_리포트.html
python3 analysis/test_analysis.py  # 분석 검증 80항목
python3 analysis/test_report.py    # 리포트 검증 81항목
```

Python(pandas, plotly) 외 런타임은 사용하지 않습니다. plotly.min.js 는 빌드 시 HTML 안에
인라인되므로 리포트는 오프라인에서 외부 요청 없이 동작합니다.

## 구성

| 파일 | 역할 |
|---|---|
| `build_data.py` | 행정구역 파싱, 동 유형 분류, 가구분화·재개발 사이클·소가구 지표 산출 |
| `build_report.py` | `parts/{head,body,js}.html` + 데이터 + plotly.js 를 단일 HTML로 조립 |
| `test_analysis.py` | 원본 CSV를 pandas 없이 독립 재파싱해 교차 검증 (무결성·항등식·계층합계·KPI·유형·사이클) |
| `test_report.py` | 리포트 검증 (JS 괄호/리터럴 균형, DOM 참조, 임베드 데이터, 본문 서술 수치 ↔ 데이터, 표시 규칙) |
| `parts/head.html` | 디자인 토큰(라이트/다크)과 레이아웃 CSS |
| `parts/body.html` | 리포트 서술과 마크업 — **본문 수치를 고치면 `test_report.py`가 데이터와 대조** |
| `parts/js.html` | Plotly 차트 12종, 구 필터, 동 탐색기, 정렬·검색 표, 테마 전환 |

## 검증 범위와 한계

`test_analysis.py` 는 남녀합=총인구, 세대당인구=인구÷세대, 동합=구합, 구합=시합을 10년 전 구간에서
확인합니다. `test_report.py` 는 본문에 쓰인 모든 수치가 데이터에서 재계산한 값과 일치하는지 대조합니다.

브라우저·JS 런타임을 쓰지 않으므로 **실제 렌더링 결과는 검증되지 않습니다.** 스크립트 문법과 DOM 참조는
정적으로 확인했으나, 차트 배치나 라벨 겹침은 브라우저에서 직접 확인해야 합니다.
