"""Build the dated literature screening report and offline web catalogue."""
from pathlib import Path
import json,html,shutil
import markdown
R=Path(__file__).resolve().parents[1]
D=R/'paper_notes'/'论文文献综述'
rows=json.loads((D/'六刊相关工作调研_20261118.json').read_text(encoding='utf-8'))
intro='''# 六个目标期刊相关工作调研与阅读路线

检索日期：2026-11-18。主要检索2023–2026年的工作，实际入选正式/在线年份以逐条记录为准。本轮精选15条：TWC 3、TCOM 2、TCCN 4、TVT 3、JSAC 2、TGCN 1。全部为待阅读线索，不改变现有已读记录。

## 范围与证据

课题基准：NGSO–NGSO–GSO异构星座下行馈电共存，固定功率下联合选星与子信道，保留GSO聚合参考窗口保护；研究重点是可靠快速干扰评价与动态决策。优先筛选卫星共存、馈电链路、动态干扰/资源决策，其次才是感知和绿色通信补充。

检索组合：satellite / feeder link / GEO LEO / NGSO + interference management / spectrum sharing / cognitive radio / dynamic resource allocation / graph / hypergraph / reinforcement learning / energy efficiency，加六刊全名或缩写；补充按完整题名和DOI追溯。使用IEEE摘要、ComSoc目录、作者高校存档、NASA/NSF记录；普通聚合站只用于发现线索，不据此判定算法成果。部分IEEE DOI无法直接解析，已在相应记录说明。

这是定向文献筛选和阅读规划，不是穷尽检索或全文系统综述。不同条目的核验深度不同，逐条列出；没有按引用量排序，也不声称未发现的方向不存在。

P1：优先精读/准备基线；P2：特定模块阅读；P3：拓展方向。相关程度和可迁移性是结合本项目作出的研究判断，不是作者结论。

## 建议阅读顺序

1. R04：已有本地PDF，先把ILP、运营约束和规模化求解作为非AI强基线。
2. R02：理解GEO–LEO共享的保护对象与认知决策闭环。
3. R03：已有本地PDF，分析动态超图是否真正减少构图和物理评价成本。
4. R01：直接涉及馈电/用户链路，学习耦合分解与MADRL可扩展性。
5. R05、R12：多域干扰管理和跳波束调度，对照服务规模、停用与时域动作。
6. R06：补齐聚合干扰、频谱泄漏与保护尾部风险的物理分析视角。
7. R07–R11按需读；R13–R15作为保护制度、结构化优化、绿色通信拓展。

## 逐篇阅读卡
'''
parts=[intro]
for r in rows:
 parts.append(f"\n### {r['id']} · {r['priority']} · {r['title']}\n\n- 期刊/年份：{r['journal']}，{r['year']}。\n- 作者：{r['authors']}。\n- 关键词：{' / '.join(r['tags'])}。\n- 阅读状态：待阅读；核验深度：{r['evidence']}。\n- 已核验内容：{r['summary']}\n- 对本项目的阅读价值【研究判断】：{r['relevance']}\n- 迁移边界：{r['boundary']}\n- 精读时的问题：{r['question']}\n- [一手来源]({r['source']})"+(f"；[DOI入口](https://doi.org/{r['doi']})" if r['doi'] else '')+(f"；[作者开放版本/获取入口]({r['access']})" if r['access'] else '')+'。\n'+(f"- 已有本地PDF：`paper_notes/阅读论文原文/{r['local']}`。\n" if r['local'] else ''))
parts.append('''
## 额外跟踪：发表状态需再核对

- [Digital-Twin-Aided Dynamic Spectrum Sharing and Resource Management in Integrated Satellite-Terrestrial Networks](https://arxiv.org/abs/2602.09191)，2026，arXiv v2（7月15日）仍写“Submitted to TWC”。另有聚合索引给出期刊DOI，但本轮未获取IEEE一手确认，故不计入15篇已定位期刊清单。方法是时间窗预测规划加实时反馈修正，使用压缩感知和SCA；它说明动态决策不必自动等于神经网络。适合借鉴“粗计划—快速修正”的时间尺度划分，不能直接声称加速我们的EPFD预算。
- [AoI-Aware Energy Efficiency Resource Allocation for Integrated Satellite-Terrestrial IoT Networks](https://www.comsoc.org/system/files/2025-03/Publications_Contents_Digest_2025_Mar.pdf)，TGCN 2025，9(1):125–139，作者Qingming Wang、Xiao Liang、Hua Zhang、Linghui Ge。官方目录题名线索，尚未核对摘要/方法，作为能效与信息新鲜度补充，不计入上述详细卡片。

## 与现有研究的对比结论【研究判断】

- 直接含馈电链路的是R01；最接近异构轨道共享的是R02、R05；最值得比较动态结构表示的是R03。三者都不自动等价于当前NGSO–GSO参考窗口聚合EPFD问题。
- 构图、完整干扰预算、求解/推理是不同成本，不能仅比较神经网络推理时间。我们应记录预处理、精确校验、失败回退和整次决策端到端耗时。
- 普通图/超图和DRL是否保证聚合保护，需要逐篇看约束形式；硬约束、奖励惩罚、平均违约和瞬时逐接收点保证不能混用。
- 本轮未确认一篇同时覆盖我们的双端方向图、NGSO–NGSO–GSO聚合保护、固定服务规模联合选星分频、误差可控增量评价的完全同题工作；这不是创新性证明，下一轮应沿上述论文参考文献和被引继续检索。
- 若目标TGCN，需要真实能耗或能效建模；缩短程序时间本身不能作为绿色贡献。若目标TCCN，应明确可观测状态、感知/推理、决策、执行反馈及不确定性。

## 精读记录模板

逐篇补充：版本/页码 → 链路方向与受保护对象 → 物理预算 → 聚合方式 → 决策变量 → 瞬时/长期约束 → 状态与动作 → 算法/训练 → 强基线 → 时间与规模 → 误差/违约/服务公平性 → 可复现材料。阅读完成后再加入已读PDF/MD配对库，不能把筛选卡称作已完成精读。
''')
report='\n'.join(parts)
md=D/'六刊相关工作调研与阅读路线_20261118.md';md.write_text(report,encoding='utf-8')
O=R/'可视化页面'/'papers'/'survey';O.mkdir(exist_ok=True)
shutil.copy2(md,O/'survey.md'); shutil.copy2(D/'六刊相关工作调研_20261118.json',O/'catalog.json')
css='''*{box-sizing:border-box}body{background:#0b1523;color:#dce8f4;font:16px/1.8 system-ui;margin:0}main{max-width:1150px;margin:auto;padding:30px 24px}a{color:#79dfce}h1{font-size:32px}h2{font-size:22px}input,select{background:#12273b;color:white;border:1px solid #35546f;padding:12px;border-radius:8px;font:inherit}input{flex:1;min-width:200px}.filters{display:flex;gap:12px;flex-wrap:wrap;position:sticky;top:0;background:#0b1523;padding:16px 0}.card{border:1px solid #35546f;border-radius:14px;background:#12273b;padding:24px;margin:20px 0}.muted{color:#a5bdd3}nav{display:flex;flex-wrap:wrap;gap:20px}table{display:block;overflow:auto}td,th{border:1px solid #35546f;padding:8px}article{overflow-wrap:anywhere}summary{cursor:pointer;color:#79dfce}'''
cards=[]
for r in rows:
 e=lambda k:html.escape(r[k])
 local=''
 if r['local']:
  pdf=R/'paper_notes'/'阅读论文原文'/r['local']
  if pdf.exists():
   shutil.copy2(pdf,O/(r['id']+'.pdf'));local=f'<a href="{r["id"]}.pdf" target="_blank">已有本地 PDF</a>'
 cards.append(f'<section class="card" data-j="{r["journal"]}" data-p="{r["priority"]}" data-search="{html.escape(json.dumps(r,ensure_ascii=False),quote=True)}"><p class="muted">{e("id")} · {e("journal")} · {e("year")} · {e("priority")} · 待阅读</p><h2>{e("title")}</h2><p>{e("authors")}</p><p>{html.escape(" / ".join(r["tags"]))}</p><p>{e("summary")}</p><p><b>为何读：</b>{e("relevance")}</p><details><summary>迁移边界与精读问题</summary><p>{e("boundary")}</p><p>{e("question")}</p><p class="muted">核验：{e("evidence")}</p></details><nav><a href="{e("source")}" target="_blank" rel="noopener">一手来源 / 获取原文</a>'+ (f'<a href="https://doi.org/{e("doi")}" target="_blank">DOI</a>' if r['doi'] else '')+local+'</nav></section>')
head='<a href="../">← 论文与综述库</a><h1>六刊相关工作 · 阅读清单</h1><p>2026-11-18 检索 · 15篇筛选卡 + 2条跟踪线索 · P1优先精读 / P2模块参考 / P3方向拓展</p><p class="muted">聚焦NGSO–NGSO–GSO下行馈电共存、可靠快速评价与动态决策。筛选依据为逐条标注的一手摘要或记录，不代表全文精读完成。</p><nav><a href="report.html">阅读完整调研与路线</a><a href="survey.md" download>下载调研 Markdown</a><a href="catalog.json" download>下载文献目录 JSON</a></nav><div class="filters"><input id="q" aria-label="搜索文献" placeholder="搜索标题、关键词、方法或作者"><select id="journal" aria-label="期刊筛选"><option value="">全部六刊</option>'+''.join('<option>'+j+'</option>' for j in ['TWC','TCOM','TCCN','TVT','JSAC','TGCN'])+'</select><select id="priority" aria-label="阅读优先级"><option value="">全部优先级</option><option>P1</option><option>P2</option><option>P3</option></select></div><p id="count"></p>'
js='''<script>const q=document.querySelector('#q'),j=document.querySelector('#journal'),p=document.querySelector('#priority'),cards=[...document.querySelectorAll('.card')];function filter(){for(const c of cards)c.hidden=!!((j.value&&c.dataset.j!==j.value)||(p.value&&c.dataset.p!==p.value)||!c.dataset.search.toLowerCase().includes(q.value.toLowerCase()));document.querySelector('#count').textContent='显示 '+cards.filter(c=>!c.hidden).length+' / '+cards.length+' 篇'}q.oninput=j.onchange=p.onchange=filter;filter();</script>'''
def page(title,body): return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+css+'</style><main>'+body+'</main></html>'
(O/'index.html').write_text(page('六刊文献调研 · 阅读清单',head+''.join(cards)+js),encoding='utf-8')
(O/'report.html').write_text(page('六刊相关工作调研与阅读路线','<a href="./">← 筛选文献</a><article>'+markdown.markdown(report,extensions=['tables','fenced_code'])+'</article>'),encoding='utf-8')
index=R/'可视化页面'/'papers'/'index.html';s=index.read_text(encoding='utf-8');link='<section class="card"><h2>六个目标期刊 · 相关工作调研</h2><p>15篇待阅读论文，支持期刊、优先级与关键词筛选；另附阅读路线和核验边界。</p><a href="survey/">打开调研阅读清单 →</a></section>'
if 'href="survey/"' not in s:s=s.replace('<label for="search">',link+'<label for="search">')
index.write_text(s,encoding='utf-8')
print('Built 15-record survey, report and local PDF links')
