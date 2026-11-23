from pathlib import Path
import json, re, shutil, html
import markdown
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'可视化页面'/'papers'
OUT.mkdir(exist_ok=True)
record={
 'id':'2505.12429v1','title':'Time-Continuous Frequency Allocation for Feeder Links of Mega Constellations with Multi-Antenna Gateway Stations',
 'authors':'Zijun Liu, Yafei Wang, Tianhao Fang, Wenjin Wang, Zhili Sun','year':2025,'status':'已读',
 'tags':['下行馈电','巨型星座','GG / CTS','连续时间分频'],
 'pdf':'paper_notes/阅读论文原文/2505.12429v1.pdf',
 'review':'paper_notes/论文精读_下行馈电干扰建模_GG_CTS及科研切入点.md'
}
registry=ROOT/'paper_notes'/'论文文献综述'/'library.json'
if registry.exists(): records=json.loads(registry.read_text(encoding='utf-8'))
else: records=[record]; registry.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
css='''*{box-sizing:border-box}body{margin:0;background:#0b1523;color:#dce8f4;font:16px/1.8 system-ui}main{max-width:1100px;margin:auto;padding:36px 24px}a{color:#79dfce}h1{font-size:32px;line-height:1.4}h2{margin-top:40px}nav{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}nav a,.tag{padding:6px 14px;border:1px solid #35546f;border-radius:8px;text-decoration:none}.card{padding:26px;border:1px solid #35546f;border-radius:14px;background:#12273b;margin:20px 0}.muted{color:#9eb3c9}input{width:100%;padding:14px;background:#12273b;color:white;border:1px solid #35546f;border-radius:8px;font-size:16px}table{display:block;overflow:auto;border-collapse:collapse}td,th{border:1px solid #35546f;padding:9px}blockquote{border-left:3px solid #79dfce;margin:20px 0;padding:12px 20px;background:#12273b}pre{overflow:auto;padding:18px;background:#07101a}img{max-width:100%}.missing{padding:14px;border:1px dashed #a98856;color:#e2c794}iframe{width:100%;height:80vh;border:1px solid #35546f}article{overflow-wrap:anywhere}article p{max-width:95ch}.toc ul{columns:2}.toc a{font-size:14px}@media(max-width:650px){.toc ul{columns:1}h1{font-size:25px}}'''
def page(title,body,extra=''):
 return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+css+'</style><main>'+body+'</main>'+extra+'</html>'
cards=[]
for r in records:
 dest=OUT/r['id']; dest.mkdir(exist_ok=True)
 shutil.copy2(ROOT/r['pdf'],dest/'original.pdf')
 shutil.copy2(ROOT/r['review'],dest/'review.md')
 raw=(ROOT/r['review']).read_text(encoding='utf-8-sig')
 # Missing historical figure assets must not appear as broken images.
 raw=re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',lambda m:'<div class="missing">'+html.escape(m[1])+'：历史图片附件未归档，请在<a href="original.pdf" target="_blank">论文 PDF</a> 中查阅。</div>' if not (ROOT/r['review']).parent.joinpath(m[2]).exists() else m[0],raw)
 math=[]
 def save(m):
  math.append(m.group()); return 'MATHPLACEHOLDER'+str(len(math)-1)+'END'
 raw=re.sub(r'\$\$[\s\S]*?\$\$|(?<!\$)\$(?!\$)[^\n$]+?\$',save,raw)
 rendered=markdown.markdown('[TOC]\n'+raw,extensions=['tables','fenced_code','toc','sane_lists'],extension_configs={'toc':{'title':'阅读目录','toc_depth':'2-3'}})
 rendered=rendered.replace('<div class="toc">','<details class="toc"><summary>展开阅读目录</summary><div>').replace('</div>\n<h1', '</div></details>\n<h1',1)
 for i,m in enumerate(math): rendered=rendered.replace('MATHPLACEHOLDER'+str(i)+'END',html.escape(m))
 mathjs='''<script>window.MathJax={tex:{inlineMath:[['$','$']],displayMath:[['$$','$$']]}};</script><script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>'''
 title=html.escape(r['title']); authors=html.escape(r['authors'])
 nav='<nav><a href="../?view=reviews">← 综述库</a><a href="original.pdf" target="_blank">阅读原文 PDF</a><a href="review.md" download>下载 Markdown</a></nav>'
 (dest/'index.html').write_text(page('论文精读 · '+r['id'],nav+'<p class="muted">已读 · 用户已有精读记录 · 按原 Markdown 内容展示；公式排版需联网加载 MathJax。</p><article>[TOC]'+rendered+'</article>',mathjs).replace('[TOC]',markdown.markdown('[TOC]\n'+raw,extensions=['toc']).split('<h1')[0] if False else ''),encoding='utf-8')
 (dest/'pdf.html').write_text(page('论文原文 · '+r['id'],'<a href="../">← 论文库</a><h1>'+title+'</h1><nav><a href="original.pdf" target="_blank">新窗口阅读 / 下载 PDF</a><a href="index.html">阅读精读综述</a></nav><iframe title="论文PDF" src="original.pdf"></iframe>'),encoding='utf-8')
 cards.append('<section class="card" data-search="'+html.escape(' '.join([r['title'],r['authors'],r['id']]+r['tags']),quote=True)+'"><p class="muted">'+r['id']+' · '+str(r['year'])+' · '+r['status']+'</p><h2>'+title+'</h2><p>'+authors+'</p><p>'+ ' · '.join(r['tags'])+'</p><nav><a href="'+r['id']+'/pdf.html">阅读 PDF 原文</a><a href="'+r['id']+'/index.html">阅读精读综述</a><a href="'+r['id']+'/review.md" download>下载 MD</a></nav></section>')
body='<a href="../">← 可视化档案首页</a><h1 id="heading">相关论文阅读库</h1><p class="muted">原文以 PDF 保存，综述以 Markdown 保存。首篇收录已有阅读记录，后续按同一目录扩充。</p><nav><a href="?view=papers">论文原文库 · '+str(len(records))+'</a><a href="?view=reviews">论文综述库 · '+str(len(records))+'</a></nav><label for="search">查找论文</label><input id="search" placeholder="搜索标题、作者、关键词或 arXiv 编号"><div id="list">'+''.join(cards)+'</div><p id="empty" hidden>暂无匹配论文。</p>'
js='''<script>const q=document.getElementById('search'),cards=[...document.querySelectorAll('.card')];if(new URLSearchParams(location.search).get('view')==='reviews')document.getElementById('heading').textContent='论文综述库';q.oninput=()=>{cards.forEach(c=>c.hidden=!c.dataset.search.toLowerCase().includes(q.value.toLowerCase()));document.getElementById('empty').hidden=cards.some(c=>!c.hidden)};</script>'''
(OUT/'index.html').write_text(page('论文原文与综述库',body,js),encoding='utf-8')
home=ROOT/'可视化页面'/'index.html'; s=home.read_text(encoding='utf-8'); anchor='<a class="card hero" href="papers/"><b>阅读与研究积累</b><h2>论文原文库 · 论文综述库</h2><p>PDF 原文、Markdown 精读记录与研究切入点 · 已读论文持续归档</p></a>'
if 'href="papers/"' not in s:s=s.replace('<div class="grid">',anchor+'<div class="grid">')
home.write_text(s,encoding='utf-8')
print('Built',len(records),'paper records')

# Refresh the research catalogue link when rebuilding the paired reading library.
survey_builder=ROOT/'scripts'/'build_literature_survey.py'
if survey_builder.exists():
    import runpy
    runpy.run_path(str(survey_builder),run_name='__main__')
