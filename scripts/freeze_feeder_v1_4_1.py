"""Create V1.4.1 research snapshot once; subsequent runs verify it, never overwrite."""
import hashlib,json,platform,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'em-situational-system-main/em-situational-system-main'
BUNDLE=ROOT/'baselines/feeder_v1_4_1_20261117'
MANIFEST=BUNDLE/'manifest.json'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def verify():
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    for item in m['files']:
        p=BUNDLE/item['path']
        if not p.is_file() or p.stat().st_size!=item['size_bytes'] or digest(p)!=item['sha256']:
            raise RuntimeError('Frozen snapshot mismatch: '+str(p))
    expected=(BUNDLE/'manifest.sha256').read_text().split()[0]
    if digest(MANIFEST)!=expected:raise RuntimeError('Manifest hash mismatch')
    print(json.dumps(dict(status='VERIFIED',bundle=str(BUNDLE),files=len(m['files']),bytes=sum(i['size_bytes'] for i in m['files']),manifest_sha256=digest(MANIFEST)),indent=2))

if MANIFEST.exists():
    verify();sys.exit(0)
if BUNDLE.exists():raise SystemExit('Partial snapshot exists; inspect it. This script never overwrites.')
# Verify original feeder_v1 before touching the new bundle.
old_manifest=PROJECT/'data/baselines/feeder_v1/manifest.json'
for item in json.loads(old_manifest.read_text(encoding='utf-8'))['files']:
    if digest(PROJECT/item['path'])!=item['sha256']:raise RuntimeError('Original feeder_v1 modified')

files=set()
def add(path):
    if path.is_file():files.add(path.resolve())
    else:raise FileNotFoundError(path)
def tree(path,patterns):
    for pattern in patterns:
        for f in path.rglob(pattern):
            if f.is_file() and '__pycache__' not in f.parts:add(f)

tree(PROJECT/'backend/app',['*.py'])
tree(PROJECT/'backend/tests',['test_feeder*.py'])
for name in ['requirements.txt','requirements-dev.txt']:add(PROJECT/'backend'/name)
tree(ROOT/'scripts',['*feeder*.py'])
tree(ROOT/'研究进展',['*.md','*.json','*.png'])
add(ROOT/'paper_notes/第一版冻结实验配置_feeder_v1.md')
for directory in sorted((ROOT/'results').glob('feeder*')):
    if directory.is_dir():tree(directory,['*'])
tree(PROJECT/'data/baselines/feeder_v1',['*'])
for name in ['feeder_baseline_v1.json','three_constellations.json']:
    path=PROJECT/'data/scenarios'/name;add(path)
    scene=json.loads(path.read_text(encoding='utf-8-sig'))
    for group in scene['constellation']['groups']:add((path.parent/group['source']).resolve())
# The profile and original input hashes must match the recorded EPFD run.
config=json.loads((ROOT/'results/feeder_gso_epfd_v1_4_1/config.json').read_text())
for key,path in [('association_sha256',ROOT/'results/feeder_association_v1_1/associations.json'),('profile_sha256',ROOT/'results/feeder_antenna_sensitivity_v1_2/selected_profile.json')]:
    if digest(path)!=config[key]:raise RuntimeError('EPFD input drift: '+str(path))
for relative,expected in config['source_hashes'].items():
    if digest(ROOT/relative)!=expected:raise RuntimeError('EPFD implementation drift: '+relative)
# Run only the research checks required by this snapshot.
tests=sorted((PROJECT/'backend/tests').glob('test_feeder*.py'))
import os
env=os.environ.copy();env['PYTHONPATH']=str(PROJECT/'backend')
run=subprocess.run([sys.executable,'-m','pytest',*[str(p) for p in tests],'-q'],cwd=ROOT,env=env,text=True,capture_output=True)
print(run.stdout)
if run.returncode:print(run.stderr);raise SystemExit(run.returncode)
BUNDLE.mkdir(parents=True)
for source in sorted(files):
    relative=source.relative_to(ROOT);dest=BUNDLE/'workspace'/relative
    dest.parent.mkdir(parents=True,exist_ok=True);before=digest(source);shutil.copy2(source,dest)
    if digest(dest)!=before or digest(source)!=before:raise RuntimeError('Copy mismatch: '+str(source))
(BUNDLE/'validation.txt').write_text('Command: '+subprocess.list2cmdline([sys.executable,'-m','pytest',*[str(p.relative_to(ROOT)) for p in tests],'-q'])+'\n'+run.stdout+run.stderr,encoding='utf-8')
packages=subprocess.run([sys.executable,'-m','pip','list','--format=json','--disable-pip-version-check'],capture_output=True,text=True)
(BUNDLE/'environment.json').write_text(json.dumps(dict(python=sys.version,executable=sys.executable,platform=platform.platform(),processor=platform.processor(),packages=json.loads(packages.stdout) if packages.returncode==0 else [],package_inventory_status=packages.returncode),indent=2),encoding='utf-8')
(BUNDLE/'README.md').write_text('''# V1.4.1研究计算冻结快照

冻结日期：2026-11-17。快照保留工作区相对目录结构于workspace/，并附测试、环境和逐文件SHA256。

## 核验

从原项目根目录运行 `.venv-ems/Scripts/python.exe scripts/freeze_feeder_v1_4_1.py`。再次运行只核验快照，不重跑仿真、不覆盖文件。manifest.sha256校验manifest，manifest校验所有载荷文件。SHA256用于完整性审计，不是数字签名或文件系统防写保护。

## 内容与范围

包含backend/app Python源码、feeder测试、相关脚本、研究记录与用户截图、各feeder阶段已有输入和结果、原feeder_v1及扩展场景引用轨道、依赖声明及实际包版本。未打包虚拟环境、数据库、服务日志或整个网页系统；这是研究基准快照，不是完整应用部署镜像。没有执行扩大规模实验或网页建设。

## 再运行

使用兼容Python环境与environment.json记录的依赖，从workspace根运行保留的scripts入口。主脚本仍有固定相对输出路径，因此不要在冻结workspace内直接运行写结果的入口。先将workspace复制到新的派生工作目录，再复现或开发；原始快照与feeder_v1不得覆盖。

现有GSO入口：scripts/run_feeder_gso_epfd.py；其输入、配置及代码哈希已在冻结时核对。测试通过记录见validation.txt。

legacy_bridge_validation.json为此前单独执行的桥接核验记录，主GSO入口不自动生成该文件。

## 已知边界与后续

该模型适于动态快速计算算法对比，不是完整ITU合规审查。10秒采样值不代表槽内连续变化；固定研究假设和参考窗口保持显式。后续按“下一步实验步骤与新对话接续_V1_4_1冻结后_20261117.md”创建派生实验。
''',encoding='utf-8')
payload=[p for p in BUNDLE.rglob('*') if p.is_file()]
m=dict(snapshot_id='feeder_v1_4_1_20261117',created_utc=datetime.now(timezone.utc).isoformat(),original_feeder_v1_manifest_sha256=digest(old_manifest),scope='research snapshot; no expansion experiment executed',files=[dict(path=p.relative_to(BUNDLE).as_posix(),size_bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(payload)])
MANIFEST.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
(BUNDLE/'manifest.sha256').write_text(digest(MANIFEST)+'  manifest.json\n',encoding='ascii')
verify()
