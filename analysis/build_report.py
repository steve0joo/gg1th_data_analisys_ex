# -*- coding: utf-8 -*-
"""리포트 조립: head + 테마부트 + body + plotly(인라인) + js(+데이터)"""
import io, json, os, plotly
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
HERE = os.path.join(ROOT, "analysis")


S = os.path.join(HERE, 'parts')
OUT = os.path.join(ROOT, '성남시_인구구조_분석_리포트.html')

rd = lambda n: io.open(os.path.join(S, n), encoding='utf-8').read()
head, body, js = rd('head.html'), rd('body.html'), rd('js.html')
data = io.open(os.path.join(HERE, 'data.json'), encoding='utf-8').read()

plotly_js = io.open(
    os.path.join(os.path.dirname(plotly.__file__), 'package_data', 'plotly.min.js'),
    encoding='utf-8').read()

# 페인트 전에 테마를 확정해 깜빡임 방지 (저장값 → 없으면 OS 설정)
boot = """<script>
(function(){try{
  var m=localStorage.getItem('snPopTheme');
  if(!m) m=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
  document.documentElement.setAttribute('data-theme',m);
}catch(e){}})();
</script>
"""

assert '__DATA__' in js
js = js.replace('__DATA__', data)

html = (head
        + boot
        + body
        + '<script>\n' + plotly_js + '\n</script>\n'
        + js)

io.open(OUT, 'w', encoding='utf-8').write(html)
print('생성:', OUT)
print('크기: %.1f MB' % (os.path.getsize(OUT) / 1024 / 1024))
print('데이터 JSON: %.0f KB' % (len(data.encode()) / 1024))
