"""Paper-style pseudocode and flowchart for the measured scan; no new simulation."""
from pathlib import Path
import hashlib,json,shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch,Polygon,FancyArrowPatch,Rectangle

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/feeder_first_frame_scan_20261117'
WEEK=ROOT/'周报素材/20261118_V1_5首帧分频扫描'
PAGE=ROOT/'可视化页面/首帧分频扫描_20261117'
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams.update({'font.family':font_manager.FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name(),'axes.unicode_minus':False,'svg.fonttype':'none'})

def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=220,bbox_inches='tight',facecolor='white')
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig)

def pseudocode():
    lines=[
    ('输入：固定首帧几何、关联、功率，原始分配 C0；随机预算 M=100，局部预算 L=100。',0,False),
    ('输出：按GSO可行优先规则保留的方案 C*；全部201次候选评价记录。',0,False),
    ('r* ← Evaluate(C0)；C* ← C0；Visited ← {C0}；记录原始方案。',0,True),
    ('for i = 1,…,M do                         // 全局随机探索',0,True),
    ('对每个网关，将8个频道随机排列，取前 k_g 个分配给该站活动链路，得到 C′。',1,True),
    ('要求 C′ 尚未出现，且各网关内无重复频道。',1,True),
    ('r′ ← Evaluate(C′)；Visited ← Visited ∪ {C′}；记录分配、指标和耗时。',1,True),
    ('if Score(r′) <lex Score(r*) then  (C*, r*) ← (C′, r′)。',1,True),
    ('end for',0,True),
    ('for j = 1,…,L do                         // 从当前保留方案产生局部候选',0,True),
    ('repeat',1,True),
    ('C′ ← C*。',2,True),
    ('if j 为奇数且 C* 存在失效链路 then',2,True),
    ('随机选取一条失效链路，令 g 为其服务网关。',3,True),
    ('else  从全部活动网关中随机选取 g。',2,True),
    ('if g 有空闲频道且 U(0,1)<0.35 then',2,True),
    ('随机选一条站内链路，改用一个随机空闲频道。',3,True),
    ('else  随机选两条站内链路，交换其频道。',2,True),
    ('until C′ 未出现于 Visited                 // 重复方案重新生成，不占评价次数',1,True),
    ('r′ ← Evaluate(C′)；Visited ← Visited ∪ {C′}；记录分配、指标和耗时。',1,True),
    ('if Score(r′) <lex Score(r*) then  (C*, r*) ← (C′, r′)。',1,True),
    ('end for；返回 C*、r* 与完整评价记录。',0,True),
    ]
    fig,ax=plt.subplots(figsize=(13,12.8));ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
    ax.plot([0,.995],[.965,.965],color='black',lw=1.8)
    ax.text(.01,.977,'算法 1  随机探索与局部改良的子信道分配启发式基线',fontsize=16,weight='bold',va='bottom')
    ax.plot([0,.995],[.945,.945],color='black',lw=.8)
    y=.925;number=0
    for text,indent,numbered in lines:
        if numbered:number+=1;ax.text(.018,y,f'{number:02}',fontsize=10,color='#555',va='top')
        ax.text(.06+indent*.035,y,text,fontsize=11.1,va='top')
        y-=.0305
    ax.plot([0,.995],[y+.007,y+.007],color='black',lw=.8)
    detail=[
      'Evaluate(C)：完整NGSO逐对预算 + GSO参考窗口EPFD + 聚合指标；每个候选重新计算。',
      'Score(r)：若GSO可行，取 (0, F, Δ)；否则取 (1, Δ, V, F)；按词典序由小到大择优。',
      'F：NGSO失败链路数；Δ：GSO最坏超限裕量（dB）；V：超限接收配置数。',
      'GSO可行：12站×1/2/5m×40kHz/1MHz的全部已评价窗口合计EPFD不超过匹配参考上限。',
      'C*是按上述规则保留的最好已评价方案，不表示已求得全局最优或满足GSO保护。',
      '随机种子20261117；局部生成最多尝试10000次，无法找到新候选时报错。',
      '201次=原始1次+随机100次+局部100次；不代表接受201次更新，也不代表必要计算次数。',
    ]
    for text in detail:
        y-=.006;ax.text(.015,y,text,fontsize=9.5,va='top',color='#303b47');y-=.021
    ax.plot([0,.995],[y+.002,y+.002],color='black',lw=1.8)
    save(fig,'算法1_分频启发式伪代码')

def flowchart():
    fig,ax=plt.subplots(figsize=(17,11));ax.set_xlim(0,17);ax.set_ylim(0,11);ax.axis('off')
    def box(x,y,w,h,text,fill='white',fs=11):
        ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=0.03,rounding_size=0.09',linewidth=1.15,edgecolor='#243744',facecolor=fill))
        ax.text(x,y,text,ha='center',va='center',fontsize=fs,linespacing=1.6)
    def diamond(x,y,w,h,text):
        ax.add_patch(Polygon([(x,y+h/2),(x+w/2,y),(x,y-h/2),(x-w/2,y)],closed=True,facecolor='#f6f8fa',edgecolor='#243744',lw=1.1))
        ax.text(x,y,text,ha='center',va='center',fontsize=10)
    def arrow(points,label=None,at=None):
        for a,b in zip(points[:-2],points[1:-1]):ax.plot([a[0],b[0]],[a[1],b[1]],color='#354d5c',lw=1.1)
        ax.add_patch(FancyArrowPatch(points[-2],points[-1],arrowstyle='-|>',mutation_scale=13,lw=1.1,color='#354d5c'))
        if label:ax.text(*(at or points[-2]),label,fontsize=10,ha='center',va='center',bbox=dict(facecolor='white',edgecolor='none',pad=1))
    ax.text(8.5,10.65,'随机探索＋随机局部改良：首帧子信道分配决策流程',ha='center',fontsize=18,weight='bold')
    box(8.5,9.85,15,.75,'固定首帧位置、选星关联与功率；站内无重频、站间复用；评价原始方案并初始化当前保留解 C*',fill='#eef5f8')
    ax.text(4.2,9.13,'阶段一：100次全局随机探索',ha='center',fontsize=13,weight='bold')
    ax.text(11.65,9.13,'阶段二：100次局部候选尝试',ha='center',fontsize=13,weight='bold')
    arrow([(1.0,9.44),(1.0,8.85),(4.2,8.85),(4.2,8.8)])
    diamond(4.2,8.35,3.4,.9,'随机候选数 i ≤ 100？')
    box(4.2,7.25,4.8,.8,'全部网关分别随机排列8频道\n按各站活动链路数取前 k_g 个')
    arrow([(4.2,7.9),(4.2,7.68)],'是',(4.5,7.79))
    box(4.2,6.05,4.8,.8,'完整计算NGSO与GSO干扰\n记录LF、EPFD及本次耗时',fill='#edf6f2')
    arrow([(4.2,6.82),(4.2,6.48)])
    diamond(4.2,4.8,4.1,1.05,'候选按Score词典序\n优于当前保留解？')
    arrow([(4.2,5.62),(4.2,5.36)])
    box(4.2,3.5,4.8,.75,'是：替换当前保留解 C*\n否：保留原 C*')
    arrow([(4.2,4.25),(4.2,3.91)])
    box(4.2,2.4,4.8,.65,'记录候选；i ← i + 1')
    arrow([(4.2,3.1),(4.2,2.76)])
    arrow([(1.77,2.4),(.65,2.4),(.65,8.35),(2.47,8.35)])
    arrow([(5.93,8.35),(9.64,8.35)],'否：进入局部阶段，j=1',(7.8,8.55))
    diamond(11.65,8.35,3.95,.9,'局部候选数 j ≤ 100？')
    box(11.65,7.1,5.8,.95,'奇数轮：选一条失效链路的网关*\n偶数轮：随机选择活动网关\n均从当前保留解 C* 出发',fs=10.5)
    arrow([(11.65,7.9),(11.65,7.62)],'是',(11.95,7.78))
    box(11.65,5.65,5.8,1.05,'若有空闲频道且随机数<0.35：改一条链路\n否则：随机交换站内两条链路的频道\n重复候选重新生成，保持站内无重频',fs=10.2)
    arrow([(11.65,6.6),(11.65,6.22)])
    box(11.65,4.25,5.8,.8,'完整计算NGSO与GSO干扰\n记录LF、EPFD及本次耗时',fill='#edf6f2')
    arrow([(11.65,5.1),(11.65,4.68)])
    box(11.65,3.1,5.8,.75,'仅当Score更优时替换 C*\n否则保留 C*，继续尝试')
    arrow([(11.65,3.82),(11.65,3.51)])
    box(11.65,2.05,5.8,.6,'记录候选；j ← j + 1')
    arrow([(11.65,2.69),(11.65,2.39)])
    arrow([(8.72,2.05),(8.0,2.05),(8.0,8.35),(9.64,8.35)])
    arrow([(13.66,8.35),(16.2,8.35),(16.2,1.1),(14.55,1.1)],'否',(15.3,8.55))
    box(11.65,1.1,5.8,.65,'输出：当前保留方案与全部201次评价记录',fill='#eef5f8',fs=10.5)
    ax.text(.85,1.65,'统一接受规则（GSO可行优先）',fontsize=11,weight='bold',va='top')
    ax.text(.85,1.36,'可行：(0, 失败数F, 最坏超限Δ)\n不可行：(1, 最坏超限Δ, 超限配置数V, F)',fontsize=10,linespacing=1.7,va='top')
    ax.text(.85,.22,'* 奇数轮若无失效链路，则随机选网关。随机用于生成候选，完整评价决定是否接受。\n201次是预设评价预算，非必需次数或收敛证明；独立8次单源诊断不计入该预算。',fontsize=9.5,color='#43505b',linespacing=1.6)
    save(fig,'分频启发式_算法流程图')

def main():
    pseudocode();flowchart()
    note='''# 首帧子信道分配启发式：算法图说明

图对应`scripts/scan_feeder_first_frame_v1_5.py`的实际实现，不改变已完成实验。

- 原始方案评价1次，然后全局随机探索100次，最后局部候选评价100次。
- 全局随机阶段对每个网关分别排列8频道，取前k_g个；不是对全部链路独立有放回分频。
- 局部阶段奇数轮从当前方案的失效链路中随机选一条，以其网关作为调整网关；偶数轮随机选活动网关。无失效链路时回退到随机网关。
- 局部阶段不是整站洗牌：有空闲频道且随机数小于0.35时，随机链路改用随机空闲频道；否则随机交换两条站内链路的频道。被调整的链路不一定就是被选中的失效链路。
- 每个局部候选从当前保留解出发。与历史分配重复时重新生成，最多10000次生成尝试；重复生成不计一次干扰评价。
- 每个候选执行完整干扰计算。仅当Score词典序严格更小时更新当前保留解；不是100次修改都被接受。本次100个局部候选实际接受12次。
- Score：GSO可行时(0,F,Δ)，不可行时(1,Δ,V,F)。F为失败链路数，Δ为最坏超限dB，V为超限接收配置数；不是单纯按LF选择初始局部搜索方案。
- GSO参与评价与接受规则，尚未直接用于识别主要施扰源并引导候选生成。单源8频道不可行诊断在搜索前独立执行，不计入201次候选评价。
- PNG可插入周报，SVG为矢量文字版，编辑时需安装微软雅黑或替换字体。伪代码图适合论文式方法说明，流程图适合讲解搜索过程。

## 建议图注

固定几何与关联条件下，随机探索与局部改良相结合的子信道分配启发式基线。候选满足站内无重频约束，采用GSO可行优先的词典序规则接受改良，并对全部201个候选执行完整干扰评价。该预算不代表所有分配算法的必要计算次数，保留解也不代表全局最优或满足GSO保护。
'''
    (OUT/'算法图说明.md').write_text(note,encoding='utf-8')
    names=['算法1_分频启发式伪代码.png','算法1_分频启发式伪代码.svg','分频启发式_算法流程图.png','分频启发式_算法流程图.svg','算法图说明.md']
    for dest in [WEEK,PAGE]:
        for name in names:shutil.copy2(OUT/name,dest/name)
    page=PAGE/'index.html';html=page.read_text(encoding='utf-8')
    if '算法1_分频启发式伪代码.png' not in html:
        section='<h2>分频启发式决策算法</h2><p>随机探索100次＋局部候选100次；候选生成与接受规则分别描述。</p><img src="算法1_分频启发式伪代码.png" alt="论文风格算法伪代码"><img src="分频启发式_算法流程图.png" alt="启发式算法流程图"><p><a href="算法图说明.md">算法图说明</a> · <a href="算法1_分频启发式伪代码.svg">伪代码矢量图</a> · <a href="分频启发式_算法流程图.svg">流程矢量图</a></p>'
        page.write_text(html.replace('</body>',section+'</body>') if '</body>' in html else html.replace('</html>',section+'</html>'),encoding='utf-8')
    # Preserve existing audit structure and add the new artifacts/source.
    p=OUT/'manifest.json';m=json.loads(p.read_text(encoding='utf-8'));m['files']=[dict(path=f.name,bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in sorted(OUT.iterdir()) if f.is_file() and f.name!='manifest.json'];m.setdefault('source_hashes',{})[Path(__file__).name]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    root=ROOT/'可视化页面';files=[f for f in sorted(root.rglob('*')) if f.is_file() and f.name!='service.log' and f!=root/'manifest.json'];(root/'manifest.json').write_text(json.dumps(dict(files=[dict(path=f.relative_to(root).as_posix(),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files]),ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved algorithm figures to',WEEK,flush=True)

if __name__=='__main__':main()
