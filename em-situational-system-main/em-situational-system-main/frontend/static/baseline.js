const baselineBox=document.createElement('section');
baselineBox.style.cssText='border:1px solid #388d98;border-radius:10px;padding:12px;margin-bottom:16px;font-size:12px;line-height:1.8';
document.getElementById('groups').before(baselineBox);
if(!baselineMode){
    const a=document.createElement('a');a.href='?scene=baseline';a.textContent='进入冻结实验基线 v1 ↗';baselineBox.append(a);
}else{
    document.title='冻结基线 v1 · 下行馈电干扰管理';
    document.querySelector('h1').textContent='冻结实验基线 v1';
    document.getElementById('step').textContent='推进 10 秒';
    document.querySelector('#gatewayPanel small').textContent='6组同区域配对：OneWeb为FCC坐标，Starlink为社区站址。GSO为12个固定仿真参考接收站。';
    document.getElementById('gatewayDetails').textContent='冻结基线：6 + 6 + 12个接收站。Starlink社区站址精度待核实。';
    fetch('/static/feeder_baseline_v1.json').then(r=>{if(!r.ok)throw Error('配置清单读取失败');return r.json()}).then(({config:c,manifest:m})=>{
        const title=document.createElement('strong');title.textContent='已冻结 · feeder_v1';baselineBox.append(title);
        const summary=document.createElement('div');summary.style.whiteSpace='pre-line';summary.textContent=`研究：异构下行馈电干扰管理 / AI动态计算加速\n网关：Starlink 6 / OneWeb 6 / GSO 12\n频段：17.8–18.6 GHz\n资源：8 × 100 MHz；每NGSO站8副工作天线\nNGSO假设：12 dBW/载波，卫星35 dBi\n网关45.76 dBi，噪温398 K，最低仰角40°\n参考LF门限：−12.2 dB（实验判据）\nUTC历元：2026-11-13 12:00\n10秒步长 / 2小时时窗 / 种子${c.seed}\nGSO：一星一站一固定关联\n状态：仅冻结配置和轨道展示\n活动链路、方向图、干扰、着色及AI尚未启用`;
        baselineBox.append(summary);
        const detail=document.createElement('details'),label=document.createElement('summary');label.textContent='配对站距与快照哈希';detail.append(label);
        for(const pair of c.station_pairs){const line=document.createElement('div');line.textContent=`${pair.oneweb_id} ↔ ${pair.starlink_id} · ${pair.distance_km} km`;detail.append(line)}
        for(const f of m.files){const line=document.createElement('div');line.style.overflowWrap='anywhere';line.textContent=f.path.split('/').pop()+' SHA256 '+f.sha256;detail.append(line)}
        baselineBox.append(detail);
        const a=document.createElement('a');a.href='/static/feeder_baseline_v1.json';a.target='_blank';a.textContent='查看完整配置与清单';baselineBox.append(a);
        const back=document.createElement('p');const link=document.createElement('a');link.href='constellations.html';link.textContent='返回全量场景';back.append(link);baselineBox.append(back);
    }).catch(e=>{baselineBox.textContent=e.message});
}

const associationEntry=document.createElement('p');const associationLink=document.createElement('a');associationLink.href='/static/feeder_links.html';associationLink.textContent='查看派生几何选星实验 ↗';associationEntry.append(associationLink);baselineBox.after(associationEntry);
