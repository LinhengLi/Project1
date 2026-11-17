// Gateway locations and source metadata share the active scenario API.
const gatewayStyle = document.createElement('style');
gatewayStyle.textContent = 'aside{max-height:calc(100vh - 96px);overflow:auto}#gatewayPanel{border-top:1px solid #29415c;margin-top:18px;padding-top:12px}#gatewayPanel label{display:block;margin:10px 0;font-size:13px}#gatewaySearch,#gatewayList{box-sizing:border-box;width:100%;background:#132941;color:#e6efff;border:1px solid #31597c;padding:8px;border-radius:6px;margin:6px 0}#gatewayDetails{white-space:pre-line;font-size:12px;line-height:1.8}#gatewayDetails a{display:inline-block;margin-top:8px}';
document.head.append(gatewayStyle);
const gatewayPanel = document.createElement('section');
gatewayPanel.id = 'gatewayPanel';
gatewayPanel.innerHTML = '<h3>网关站 · <span id="gatewayCount">加载中</span></h3><small>大圆点为网关；白边为 FCC 来源，橙边为社区来源，蓝边为区域仿真位置。GSO 金色参考站为仿真设置，绿色虚线仅表示天线指向。</small><label><input id="showStarlinkGateways" type="checkbox" checked> Starlink 网关（218）</label><label><input id="showOnewebGateways" type="checkbox" checked> OneWeb 网关（13：6 FCC + 7仿真）</label><label><input id="showGsoGateways" type="checkbox" checked> GSO 参考接收站（12，一星一站）</label><label><input id="verifiedGateways" type="checkbox"> 仅显示资料标记已核实的站点</label><input id="gatewaySearch" placeholder="搜索站名或站点 ID" aria-label="搜索网关站"><select id="gatewayList" aria-label="选择网关站"><option value="">选择网关站查看详情</option></select><div id="gatewayDetails">OneWeb：6站FCC坐标基线 + 7个区域仿真位置。勾选“仅显示资料标记已核实的站点”可查看精确坐标集。</div>';
document.getElementById('groups').after(gatewayPanel);
let gateways = [], gatewayEntities = [];
function gatewayDetails(station, fly = false) {
    const m = station.research_metadata;
    const box = document.getElementById('gatewayDetails');
    box.textContent = `${station.name}\n${station.id} · ${station.constellation_id}\n纬度 ${station.latitude.toFixed(6)}° / 经度 ${station.longitude.toFixed(6)}°\n坐标依据：${m.position_verified ? 'FCC 文件（资料标记已核实）' : m.simulation_location ? '研究者选定的区域近似坐标，非实际天线位置' : '社区目录，位置精度未核实'}\n研究频段：${m.research_band_verified ? '17.8–18.6 GHz（资料标记）' : m.study_band_assumed ? '17.8–18.6 GHz（研究假设，逐站许可未核实）' : '未核实'}\n当前运营：${m.active_now_confirmed ? '资料已确认' : '未确认'}\n文档天线数：${m.antenna_count_documented ?? '未知'}；口径：${m.antenna_diameter_m_documented ?? '未知'} m\n实验天线数选项：${(m.simulation_antenna_counts || []).join(' / ')}\n海拔：${station.altitude_m} m（假设）`;
    if (m.simulation_reference) box.textContent = `${station.name}
${station.id}
仿真参考点；非已核实 GSO 网关
纬度 ${station.latitude}° / 经度 ${station.longitude}°
锚点：${m.anchor_station_id}
指向：${m.pointing_satellite_name}
关联策略：一星一站一链路，固定不切换
初始仰角：${m.epoch_elevation_deg}°
24h采样最低仰角：${m.minimum_sampled_elevation_24h_deg}°
假设频段：17.8–18.6 GHz
假设口径：${m.simulation_antenna_diameter_m} m；效率 ${m.simulation_aperture_efficiency}
假设增益：${m.simulation_peak_gain_dbi} dBi @18.2 GHz
假设噪温：${m.simulation_noise_temperature_k} K
波束覆盖与 EPFD 限值待配置；干扰计算未启用
金色标记抬高 3 km 仅用于区分同址点`;
    if (m.source?.url && /^https?:\/\//.test(m.source.url)) {
        const a = document.createElement('a'); a.href = m.source.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = '查看原始资料 ↗'; box.append(document.createElement('br'), a);
    }
    if(m.reported_status)box.append(document.createTextNode('\n资料状态：'+m.reported_status));
    document.getElementById('gatewayList').value = station.id;
    if (fly) viewer.camera.flyTo({destination:Cesium.Cartesian3.fromDegrees(station.longitude,station.latitude,2200000),duration:1.2});
}
function drawGateways() {
    for (const entity of gatewayEntities) viewer.entities.remove(entity);
    gatewayEntities = [];
    const query = document.getElementById('gatewaySearch').value.toLowerCase();
    const filtered = gateways.filter(g => document.getElementById(({starlink:'showStarlinkGateways',oneweb:'showOnewebGateways',gso:'showGsoGateways'})[g.constellation_id]).checked && (!document.getElementById('verifiedGateways').checked || g.research_metadata.position_verified) && (g.name+' '+g.id).toLowerCase().includes(query));
    document.getElementById('gatewayCount').textContent = filtered.length + ' / ' + gateways.length;
    const list = document.getElementById('gatewayList');list.replaceChildren(new Option('选择网关站查看详情',''));
    for (const g of filtered) {
        list.add(new Option(g.name+' · '+g.id,g.id));
        const entity = viewer.entities.add({id:'gateway:'+g.id,position:Cesium.Cartesian3.fromDegrees(g.longitude,g.latitude,g.altitude_m+(g.constellation_id==='gso'?3000:0)),point:{pixelSize:g.constellation_id==='gso'?16:11,color:Cesium.Color.fromCssColorString(colors[g.constellation_id]),outlineColor:Cesium.Color.fromCssColorString(g.constellation_id==='gso'?'#78ffa8':g.research_metadata.position_verified?'#ffffff':g.research_metadata.simulation_location?'#579dff':'#ff983e'),outlineWidth:2}});
        entity.gatewayRecord = g;
        gatewayEntities.push(entity);
        if(g.constellation_id==='gso') {
            const sat=data.find(p=>p.entity_id===g.research_metadata.pointing_satellite_id);
            if(sat)gatewayEntities.push(viewer.entities.add({polyline:{positions:[Cesium.Cartesian3.fromDegrees(g.longitude,g.latitude,g.altitude_m),Cesium.Cartesian3.fromDegrees(sat.longitude,sat.latitude,sat.altitude_m)],width:1.5,material:new Cesium.PolylineDashMaterialProperty({color:Cesium.Color.fromCssColorString('#78ffa8')})}}));
        }
    }
}
for(const id of ['showStarlinkGateways','showOnewebGateways','showGsoGateways','verifiedGateways','gatewaySearch'])document.getElementById(id).addEventListener('input',()=>{if(viewer)drawGateways()});
document.getElementById('gatewayList').onchange = e => {const g=gateways.find(g=>g.id===e.target.value);if(g)gatewayDetails(g,true)};
const refreshWithoutGateways = refresh;
refresh = async function(){await refreshWithoutGateways();const scenario=await api('/scenario/current');gateways=scenario.ground_stations;for(const [system,id] of Object.entries({starlink:'showStarlinkGateways',oneweb:'showOnewebGateways',gso:'showGsoGateways'})){const input=document.getElementById(id);input.parentElement.lastChild.textContent=' '+({starlink:'Starlink 网关',oneweb:'OneWeb 网关',gso:'GSO 参考接收站'})[system]+'（'+gateways.filter(g=>g.constellation_id===system).length+'）'}drawGateways();};
// A separate handler adds gateway picking without replacing satellite details.
const attachGatewayPicker = setInterval(()=>{if(!viewer)return;clearInterval(attachGatewayPicker);const handler=new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);handler.setInputAction(e=>{const picked=viewer.scene.pick(e.position);if(picked?.id?.gatewayRecord)gatewayDetails(picked.id.gatewayRecord)},Cesium.ScreenSpaceEventType.LEFT_CLICK)},100);
