"""Create V1.5 once; all subsequent calls verify, never overwrite."""
import hashlib,json,platform,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'em-situational-system-main/em-situational-system-main'
BUNDLE=ROOT/'baselines/feeder_v1_5_20261117'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    p=BUNDLE/'manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    assert digest(p)==(BUNDLE/'manifest.sha256').read_text().split()[0]
    for r in m['files']:
        f=BUNDLE/r['path'];assert f.stat().st_size==r['bytes'] and digest(f)==r['sha256'],r['path']
    print(json.dumps(dict(status='VERIFIED',files=len(m['files']),bytes=sum(r['bytes'] for r in m['files']),manifest_sha256=digest(p),bundle=str(BUNDLE)),ensure_ascii=False),flush=True)
if (BUNDLE/'manifest.json').exists():verify();sys.exit(0)
if BUNDLE.exists():raise SystemExit('Partial snapshot exists; inspect manually. No overwrite permitted.')
subprocess.run([sys.executable,str(ROOT/'scripts/freeze_feeder_v1_4_1.py')],check=True)
out=ROOT/'results/feeder_openloop_v1_5'
for r in json.loads((out/'manifest.json').read_text(encoding='utf-8'))['files']:
    assert digest(out/r['path'])==r['sha256'],r['path']
config=json.loads((out/'config.json').read_text(encoding='utf-8'))
assert digest(ROOT/'scripts/run_feeder_openloop_v1_5.py')==config['implementation_sha256']
tests=[ROOT/'tests/test_feeder_openloop_v1_5.py',*sorted((PROJECT/'backend/tests').glob('test_feeder*.py'))]
run=subprocess.run([sys.executable,'-m','pytest',*[str(p) for p in tests],'-q'],cwd=ROOT,text=True,capture_output=True)
print(run.stdout,flush=True)
if run.returncode:print(run.stderr);raise SystemExit(run.returncode)
files=set()
def add(p):
    p=Path(p)
    if p.is_file():files.add(p)
    else:files.update(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
for p in [out,PROJECT/'backend/app',PROJECT/'backend/requirements.txt',PROJECT/'backend/requirements-dev.txt',ROOT/'tests/test_feeder_openloop_v1_5.py',ROOT/'results/feeder_association_v1_1/associations.json',ROOT/'results/feeder_antenna_sensitivity_v1_2/selected_profile.json',PROJECT/'data/scenarios/three_constellations.json',ROOT/'研究进展/V1_5_两小时开环完整计算基准_20261117.md',ROOT/'experiments/feeder_openloop_v1_5',ROOT/'可视化页面/v1_5/index.html']:
    add(p)
for p in tests:add(p)
for p in (ROOT/'scripts').glob('*feeder*v1_5*.py'):add(p)
for r in config['sources']:add(ROOT/r['path'])
for i in [0,360,719]:add(ROOT/f'results/feeder_openloop_v1_5_replay_check_{i:03d}')
BUNDLE.mkdir(parents=True)
for p in sorted(files):
    q=BUNDLE/'workspace'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);h=digest(p);shutil.copy2(p,q);assert digest(q)==h==digest(p)
(BUNDLE/'validation.txt').write_text(' '.join([sys.executable,'-m','pytest',*[str(p.relative_to(ROOT)) for p in tests],'-q'])+'\n'+run.stdout+run.stderr,encoding='utf-8')
(BUNDLE/'environment.json').write_text(json.dumps(dict(platform=platform.platform(),python=sys.version,dependencies=config['dependencies'],threads=config['thread_environment']),indent=2),encoding='utf-8')
(BUNDLE/'README.md').write_text('''# V1.5冻结研究基准

日期：2026-11-17。720个起点快照；最大仰角选星、站内无重频随机分配；完整NGSO与GSO参考窗口计算。

workspace保留代码、输入、720帧结果、报告、测试和V1.5可视化源码。未包含虚拟环境、整个旧态势系统或全部其他版本网页。哈希用于完整性审计，不是文件系统写保护。

运行scripts/freeze_feeder_v1_5.py再次调用仅核验，不覆盖、不重跑实验。后续实验应在原工作区另建派生入口和输出目录；禁止在本冻结workspace内运行会写结果的脚本。

V1.5是开环采样研究基准，没有子信道优化、反馈、近似复用或AI；不作为连续时间保护或真实运营系统合规结论。独立的首帧优化扫描不属于本次冻结结果。
''',encoding='utf-8')
payload=[p for p in sorted(BUNDLE.rglob('*')) if p.is_file()]
m=dict(snapshot_id='feeder_v1_5_20261117',created_utc=datetime.now(timezone.utc).isoformat(),files=[dict(path=p.relative_to(BUNDLE).as_posix(),bytes=p.stat().st_size,sha256=digest(p)) for p in payload])
(BUNDLE/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
(BUNDLE/'manifest.sha256').write_text(digest(BUNDLE/'manifest.json')+'  manifest.json\n',encoding='ascii')
verify()
