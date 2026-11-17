"""S1528-0 1.2 circular-beam sensitivity; no allocation optimization."""
import runpy,json,math,csv,hashlib
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
x=runpy.run_path(str(root/'scripts/run_feeder_interference.py'))
from app.services.feeder_interference import C,K,s1528,aggregate
out=root/'results/feeder_antenna_sensitivity_v1_2';out.mkdir(exist_ok=True)
peak=35.; frequency=x['frequency']; efficiency=.6
q=math.sqrt(10**(peak/10)/(efficiency*math.pi**2))
selected=math.sqrt(1200)/q
widths=sorted(set([.5,.75,1.,1.25,1.5,1.75,2.,selected]))
base=x['result']; links=x['links']; old_gain=np.array([[s1528(t,peak,1.,-20) for t in row] for row in base['tx_offaxis_deg']])
rows=[]; details=[]
for width in widths:
    for side in [-15,-20,-25,-30]:
        gains=np.array([[s1528(t,peak,width,side) for t in row] for row in base['tx_offaxis_deg']])
        power=base['received_power_w']*10**((gains-old_gain)/10)
        for name,channels in [('all_cochannel',[0]*len(links)),('antenna_index',[r['antenna_index'] for r in links])]:
            a=aggregate(power,links,channels); ratio=np.array(a['in_linear']); db=10*np.log10(np.maximum(ratio,1e-300))
            row=dict(half_width_deg=width,hpbw_deg=2*width,sidelobe_db=side,diagnostic=name,lf_rate=a['lf_rate'],failed_count=int(sum(ratio>10**(-12.2/10))),in_db_median=float(np.median(db)),in_db_max=float(max(db)),total_interference_w=sum(a['aggregate_power_w']))
            rows.append(row);details.append(dict(**row,per_link=a))
profile=dict(version='feeder_v1_2_antenna_research_profile',model='S.1528-0 recommends 1.2',beam_axis_ratio=1,tx_peak_dbi=peak,tx_half_width_deg=selected,tx_hpbw_deg=2*selected,tx_sidelobe_db=-20,reference_frequency_hz=frequency,assumed_aperture_efficiency=efficiency,inferred_d_over_lambda=q,inferred_aperture_m=q*C/frequency,parameter_status='research assumptions, not confirmed paper values or real equipment data',selection_reason='retain -20 dB intermediate sidelobe baseline; derive width from 35 dBi and assumed efficiency 0.6 rather than tune LF on one snapshot',width_derivation='q=sqrt(10^(Gm/10)/(eta*pi^2)); half_width=sqrt(1200)/q',source_report_sha256=hashlib.sha256((root/'研究进展/ITU_S1528-0_S1428-1_天线方向图核查报告.md').read_bytes()).hexdigest(),association_sha256=x['config']['source_sha256'],sample_scope='first frame only, 66 links; nominal frequency; fixed peak across width scan',width_scan_note='width-only sweep changes implied aperture efficiency; it is a mathematical sensitivity sweep, not all points are feasible circular apertures')
(out/'selected_profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'sensitivity_details.json').write_text(json.dumps(details,indent=2),encoding='utf-8')
with (out/'sensitivity.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
angles=sorted(set(np.linspace(0,180,1801).tolist()+[0,selected,2.58*selected,6.32*selected,90,180]))
with (out/'selected_pattern.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['offaxis_deg','gain_dbi']);w.writerows((t,s1528(t,peak,selected,-20)) for t in angles)
print(json.dumps(profile,ensure_ascii=False,indent=2))
for mode in ['all_cochannel','antenna_index']:
    r=[r for r in rows if r['diagnostic']==mode]
    print(mode,'LF range',min(v['lf_rate'] for v in r),max(v['lf_rate'] for v in r))
    print('selected', [v for v in r if v['half_width_deg']==selected and v['sidelobe_db']==-20])
