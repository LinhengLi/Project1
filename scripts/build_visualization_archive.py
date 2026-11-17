"""Package independent read-only historical viewers; never rerun interference."""
import csv,gzip,hashlib,json,shutil,sys
from datetime import timedelta
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'可视化页面'
sys.path.insert(0,str(ROOT/'scripts'))
from run_feeder_openloop_v1_5 import Scene

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,o):Path(p).write_text(json.dumps(o,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')
def rows(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig',newline='')))

def main():
    OUT.mkdir(exist_ok=False)
    assoc=read(ROOT/'results/feeder_association_v1_1/associations.json')
    source=ROOT/'em-situational-system-main/em-situational-system-main/frontend/static'
    specs=[('v1_1','V1.1','几何与活动馈电关联'),('v1_2','V1.2','单快照物理干扰与天线敏感性'),('v1_3','V1.3','61帧动态物理计算与发射频率对照'),('v1_4','V1.4','GSO频道功率诊断与有界筛选'),('v1_4_1','V1.4.1','GSO参考窗口EPFD'),('v1_5','V1.5','两小时720帧开环完整计算')]
    template=(ROOT/'scripts/visualization_archive_template.html').read_text(encoding='utf-8')
    for slug,version,title in specs:
        dest=OUT/slug;dest.mkdir();(dest/'原始结果').mkdir()
        data=dict(version=version,title=title,ground_stations=assoc['ground_stations'],frames=assoc['frames'][:1] if slug=='v1_2' else assoc['frames'],modes=['antenna_index','all_cochannel'],ngso={},gso={},notes='',gso_kind='none')
        def copy(relative,name=None):
            p=ROOT/relative;shutil.copy2(p,dest/'原始结果'/(name or p.name))
        if slug=='v1_1':
            data['modes']=['geometry'];data['notes']='10分钟、61帧；6+6个NGSO网关及12个GSO参考点。仅几何和关联，未分频、未计算LF/EPFD。'
            copy('results/feeder_association_v1_1/associations.json')
        elif slug=='v1_2':
            s=read(ROOT/'results/feeder_physics_v1_2/single_slot_summary.json')
            for mode,key in [('antenna_index','antenna_index_diagnostic'),('all_cochannel','all_cochannel')]:
                v=s[key];ratio=np.array(v['in_linear']);data['ngso'][mode]=[dict(lf=v['lf_rate'],failed=int(sum(ratio>10**(-12.2/10))),in_db=[float(10*np.log10(x)) if x else None for x in ratio])]
            data['notes']='仅首帧；原始V1.2使用18.2GHz、发射半宽1°的敏感性基准。这里保留历史参数，不套用后来V1.4.1参数。'
            copy('results/feeder_physics_v1_2/single_slot_summary.json');copy('results/feeder_antenna_sensitivity_v1_2/selected_profile.json');copy('results/feeder_antenna_sensitivity_v1_2/sensitivity.csv') if (ROOT/'results/feeder_antenna_sensitivity_v1_2/sensitivity.csv').exists() else None
        elif slug=='v1_3':
            for r in read(ROOT/'results/feeder_physics_v1_3_10min/baseline_per_link.json'):
                ratio=r['per_link']['in_linear'];data['ngso'].setdefault(r['diagnostic'],[]).append(dict(lf=r['lf_rate'],failed=r['failed_links'],in_db=[float(10*np.log10(x)) if x else None for x in ratio]))
            for mode in ['antenna_index','all_cochannel']:
                values=[r for r in rows(ROOT/'results/feeder_physics_v1_3_tx_frequency/frame_comparison.csv') if r['mode']==mode]
                data['ngso'][mode+'_scaled']=[dict(lf=float(r['scaled_lf']),failed=round(float(r['scaled_lf'])*int(r['links'])),in_db=[]) for r in values]
            data['modes']+=['antenna_index_scaled','all_cochannel_scaled'];data['notes']='61帧；基础模式为跨频段固定发射角方向图，scaled模式为固定有效口径跨频率缩放的补充对照。均为历史诊断分频，不是随机优化。'
            for p in ['feeder_physics_v1_3_10min/summary.json','feeder_physics_v1_3_10min/sensitivity_timeseries.csv','feeder_physics_v1_3_tx_frequency/frame_comparison.csv','feeder_physics_v1_3_tx_frequency/summary.json']:copy('results/'+p,p.replace('/','_'))
        elif slug=='v1_4':
            rr=rows(ROOT/'results/feeder_physics_v1_4/ngso_reference.csv')
            for mode in data['modes']:
                data['ngso'][mode]=[]
                for i in range(61):
                    vals=[float(r['in_linear']) for r in rr if r['mode']==mode and int(r['frame'])==i];failed=sum(v>10**(-12.2/10) for v in vals)
                    data['ngso'][mode].append(dict(lf=failed/len(vals),failed=failed,in_db=[10*np.log10(v) if v else None for v in vals]))
            data['gso_kind']='power';data['notes']='GSO使用原3.5m设备元数据；仅按NGSO频道分箱的接收功率诊断，不是参考带宽EPFD，不绘制EPFD保护线。有界筛选原型未取得加速。'
            for r in rows(ROOT/'results/feeder_physics_v1_4/gso_channel_power.csv'):
                key=f"{r['mode']}/{r['frame']}";data['gso'].setdefault(key,[]).append(dict(receiver=r['receiver'],value=float(r['total_w']),window='channel '+r['channel']))
            for name in ['summary.json','benchmark.csv','gso_channel_power.csv']:copy('results/feeder_physics_v1_4/'+name)
        elif slug=='v1_4_1':
            data['gso_kind']='epfd';data['notes']='独立1/2/5m、40kHz/1MHz参考窗口；30个中心/边界窗口。此阶段归档GSO计算结果，页面不推填未在此入口输出的NGSO统计。'
            peaks={}
            for r in rows(ROOT/'results/feeder_gso_epfd_v1_4_1/window_epfd.csv'):
                for op in ['starlink','oneweb','combined']:
                    k=(r['mode'],r['frame'],r['diameter_m'],r['reference_bandwidth_hz'],op,r['receiver']);v=float(r[op+'_w_m2'])
                    if k not in peaks or v>peaks[k][0]:peaks[k]=(v,r['window_id'],float(r['center_hz']))
            for (mode,frame,diam,bw,op,receiver),(v,wi,f) in peaks.items():
                key=f'{mode}/{frame}';data['gso'].setdefault(key,[]).append(dict(receiver=receiver,diam=float(diam),bw=float(bw),op=op,value=v,window=f'{f/1e9:.2f} GHz / {wi}'))
            for name in ['config.json','summary.json','legacy_bridge_validation.json']:copy('results/feeder_gso_epfd_v1_4_1/'+name)
        else:
            shutil.copytree(ROOT/'results/feeder_openloop_v1_5',dest/'data')
            html=(ROOT/'experiments/feeder_openloop_v1_5/index.html').read_text(encoding='utf-8')
            html=html.replace("base=new URLSearchParams(location.search).get('pilot')==='1'?'../../results/feeder_openloop_v1_5_pilot/':'../../results/feeder_openloop_v1_5/'","base='data/'")
            html=html.replace('../../results/feeder_openloop_v1_5/','data/')
            html=html.replace('<body>','<body>') .replace('<div class="top">','<p><a href="../">← 可视化档案首页</a></p><div class="top">',1)
            (dest/'index.html').write_text(html,encoding='utf-8');continue
        write(dest/'data.json',data);(dest/'index.html').write_text(template,encoding='utf-8')
    # Independent precomputed all-catalogue orbital overview; no shared simulation API.
    dest=OUT/'giant_constellation';dest.mkdir();scene=Scene()
    write(dest/'stations.json',scene.stations)
    write(dest/'satellites.json',[dict(id=str(s),name=o.name,system=str(op)) for s,o,op in zip(scene.ids,scene.objects,scene.ops)])
    for i in range(121):
        when=scene.epoch+timedelta(seconds=i*60);ecef,eligible,audit=scene.propagate(when)
        assert np.all(np.isfinite(ecef))
        with gzip.open(dest/f'frame_{i:03d}.json.gz','wt',encoding='utf-8') as f:json.dump(dict(timestamp=when.isoformat(),positions_m=np.round(ecef,0).astype(float).tolist()),f,separators=(',',':'))
        if i%30==0:print('orbital cache',i,flush=True)
    write(dest/'config.json',dict(scope='display-only orbital cache; not new interference results',frames=121,step_seconds=60,endpoint_included=True,start_utc=scene.epoch.isoformat(),sources=scene.sources,station_counts=dict(starlink=218,oneweb=13,gso=12),satellite_counts=dict(starlink=10611,oneweb=651,gso=12),coordinate_rounding='ECEF rounded to 1m for display only; all source records retained without research altitude filtering'))
    shutil.copy2(ROOT/'scripts/visualization_giant_template.html',dest/'index.html')
    cards=''.join(f'<a class="card" href="{slug}/"><b>{version}</b><h2>{title}</h2><span>独立页面 · 独立数据副本 →</span></a>' for slug,version,title in specs)
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>研究可视化档案</title><style>body{background:#091321;color:#e0edf8;font:16px system-ui;margin:40px auto;padding:20px;max-width:1100px}h1{font-size:34px}p{color:#9fb3c8;line-height:1.8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:18px}.card{background:#13273b;border:1px solid #315371;border-radius:15px;padding:24px;color:#d9edf8;text-decoration:none}.card:hover{border-color:#64d8c0}.card b{color:#64d8c0}.card h2{font-size:20px}span{font-size:13px;color:#96aec5}.hero{display:block;margin:28px 0;background:#143c48}.hero h2{font-size:26px}</style><h1>研究可视化档案</h1><p>固定历史页面和数据副本，切换版本不改变其他页面的场景。原冻结快照与已有实验结果保持不变。</p><a class="card hero" href="giant_constellation/"><b>你要找的巨型星座总览</b><h2>Starlink + OneWeb + GSO 卫星与网关</h2><p>10611 + 651 + 12颗候选卫星 · 218 + 13 + 12个站点<br>三维地球、系统开关、网关筛选和详情、60秒轨道展示回放。</p></a><div class="grid">'''+cards+'''</div><p>V1.1–V1.4.1是旧版6+6个NGSO网关关联输入；V1.5才是扩展集合下两小时720帧干扰基准。巨型星座总览独立于这些历史实验，不把目录卫星数量当成同时活动链路数量。</p><p>使用“启动可视化.cmd”启动本地服务；关闭浏览器不会停止服务。三维页面使用Cesium和在线底图，首次打开需要网络；原始输入、历史参数及适用边界分别保留。</p></html>'''
    (OUT/'index.html').write_text(html,encoding='utf-8')
    files=[p for p in OUT.rglob('*') if p.is_file()]
    write(OUT/'manifest.json',dict(files=[dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]))
    print('archive built',len(files),'files',flush=True)

if __name__=='__main__':main()
