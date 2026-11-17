"""Evidence-backed frequency candidates; not an exhaustive worldwide inventory."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source='https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/licences-and-certificates/list-foreign-satellites-approved-provide-fixed-satellite-services-fss-canada'
# NORAD identities matched against the user's local OMM catalogue.
evidence={56371:('Arcturus',[[18.4,18.8]]),38551:('EchoStar XVII',[[18.3,18.8]]),40384:('Inmarsat-5 F2',[[17.7,20.2]]),40882:('Inmarsat-5 F3',[[17.7,20.2]]),41893:('Jupiter-2',[[18.3,19.3]]),57479:('JUPITER 3',[[18.3,19.3]]),42709:('SES-15',[[18.3,18.8]]),49332:('SES-17',[[17.3,18.8]]),43562:('TELSTAR 19V',[[17.8,18.3],[18.3,18.8]]),40613:('THOR 7',[[18.3,20.2]]),37843:('ViaSat-1',[[18.3,19.3]]),42740:('ViaSat-2',[[17.7,18.3],[18.3,18.8]])}
catalog=json.loads((root/'realdatas/geo.json').read_text(encoding='utf-8-sig'))
assert set(evidence)<= {int(r['NORAD_CAT_ID']) for r in catalog}
audit=[]; selected=[]
for r in catalog:
    n=int(r['NORAD_CAT_ID'])
    item=dict(norad_cat_id=n,name=r['OBJECT_NAME'],status='not_yet_verified',enabled_for_interference_calculation=False)
    if n in evidence:
        name,bands=evidence[n]
        overlap=[[max(17.8,a),min(18.6,b)] for a,b in bands if max(17.8,a)<min(18.6,b)]
        item.update(status='frequency_overlap_candidate',source_commercial_name=name,source_downlink_intervals_ghz=bands,overlap_intervals_ghz=overlap,source_url=source,source_scope='Canadian FSS approval table; not global authorization or proof of current transmission',pending=['operational status','beam coverage','protected earth station','actual channel allocation and antenna parameters'])
        selected.append(r)
    audit.append(item)
report=dict(review_date='2026-11-15',study_band_ghz=[17.8,18.6],catalog_count=len(catalog),candidate_count=len(selected),scope='Initial evidence-backed subset, not an exhaustive global frequency screening. Unselected does not mean out of band.',records=audit)
(root/'realdatas/GSO_17p8_18p6_screening.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'realdatas/geo_research_candidates.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# GSO 下行频段筛选（第一批）','','研究频段：17.8–18.6 GHz。筛选条件为下行频段存在正带宽交集；仅相接于 18.6 GHz 不算重叠。','',f'原目录 {len(catalog)} 颗，频段依据明确的候选 {len(selected)} 颗，其余 {len(catalog)-len(selected)} 颗待核实，未判定为不适用。','','来源：'+source,'','该表反映加拿大 FSS 批准频段，不证明全球授权、实际发射、在轨健康状态或波束照射研究网关。轨道目录也不证明业务在运行。','','|本地名称|NORAD|研究频段交集 GHz|','|---|---:|---|']
for x in audit:
    if x['status']=='frequency_overlap_candidate':lines.append(f"|{x['name']}|{x['norad_cat_id']}|{x['overlap_intervals_ghz']}|")
lines+=['','优先作为 GSO 受保护系统候选；GSO→NGSO 下行干扰须另行核对波束与发射参数。当前没有 GSO 地球站，因此所有条目的 enabled_for_interference_calculation=false。','现有 222 个 Starlink/OneWeb 网关不能替代 GSO 受保护地球站。频段候选仅用于场景筛选和显示，不计入 NGSO LF 分母，不直接作为可调度的 NGSO 着色节点。','完整证据及待核实清单见 realdatas/GSO_17p8_18p6_screening.json；geo.json 原始文件保留。']
(root/'paper_notes/GSO_17p8_18p6筛选说明.md').write_text('\n'.join(lines),encoding='utf-8')
print('Candidates:',len(selected),'Pending:',len(catalog)-len(selected))
