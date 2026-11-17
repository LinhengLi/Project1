"""Build a versioned research catalogue; do not overwrite the original four sites."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
original=json.loads((root/'realdatas/OneWeb_constellation.json').read_text(encoding='utf-8-sig'))
rows=list(original['gateway_sites'])
fcc='https://docs.fcc.gov/public/attachments/'
telstra='https://www.telstrainternational.com/en/news-research/articles/telstra-providing-satellite-ground-infrastructure-for-oneweb'
telespazio='https://www.telespazio.com/documents/559023/0/PR%2BTelespazio%2BMarica_en.pdf?t=1677688656941'
new=[
('OW-FCC-005','Clewiston SNP, Florida',26+44/60+51.8/3600,-(81+2/60+57.2/3600),True,fcc+'DOC-355200A1.pdf','FCC application SES-LIC-20180727-02075',13),
('OW-FCC-006','Santa Paula SNP, California',34+24/60+7.2/3600,-(119+4/60+23.5/3600),True,fcc+'DOC-358650A1.pdf','FCC application SES-LIC-20190422-00538; grant DOC-376504A1',20),
('OW-SIM-007','Darwin Tivendale · 仿真位置',-12.5,130.95,False,telstra,'2022 project announcement; completion not verified',None),
('OW-SIM-008','Charlton Toowoomba · 仿真位置',-27.55,151.85,False,telstra,'2022 planned gateway; completion not verified',None),
('OW-SIM-009','Wangara Perth · 仿真位置',-31.8,115.85,False,telstra,'2022 planned gateway; completion not verified',None),
('OW-SIM-010','Scanzano · 仿真位置',37.91,13.36,False,telespazio,'2023 operator statement: gateway installed; antenna-count discrepancy across languages',None),
('OW-SIM-011','Maricá · 仿真位置',-22.9,-42.8,False,telespazio,'2023 inauguration; current operation unverified',None),
('OW-SIM-012','Sirindhorn Ubon Ratchathani · 仿真位置',15.2,104.85,False,'https://www.ntsatellite.net/en/news-2/','2024 readiness announcement; exact antenna location unverified',None),
('OW-SIM-013','SvalSat · 仿真位置',78.25,15.5,False,'https://nebula.esa.int/sites/default/files/neb_tec_study/2499/public/FIGSI_Presentation_Project_Overview_at_FP_ESO_Marco%20Lanucara.pdf','2024 project presentation identifies OneWeb gateway; exact antenna location unverified',None),
]
for sid,name,lat,lon,verified,url,status,count in new:
    rows.append(dict(id=sid,name=name,latitude_deg=lat,longitude_deg=lon,altitude_m_assumed=0,coordinate_reference='WGS84',position_verified=verified,position_accuracy='fcc_filing_site_coordinates' if verified else 'manually_selected_regional_simulation_point_not_measured',coordinate_origin='FCC DMS converted to decimal degrees' if verified else 'Researcher-selected coarse geographic approximation; not extracted from source',simulation_location=not verified,research_band_verified=verified,downlink_research_band_mhz=[17800,18600],study_band_assumed=not verified,active_now_confirmed=False,reported_status=status,antenna_count_documented=count,antenna_diameter_m_documented=3.5 if verified else None,simulation_antenna_counts=[4,8,16],source=dict(title='Gateway project / regulatory evidence; approximate coordinates are not provided by this source',url=url),notes='For unverified positions, study-band use and 0m altitude are experiment assumptions. Do not treat as operational site or antenna coordinates.'))
assert len(rows)==len({r['id'] for r in rows})==13
assert all(-90<=r['latitude_deg']<=90 and -180<=r['longitude_deg']<=180 for r in rows)
result=dict(review_date='2026-11-15',system='OneWeb',gateway_sites=rows,gateway_count=13,verified_coordinate_count=6,simulation_location_count=7,profiles=dict(strict_fcc=[r['id'] for r in rows if r['position_verified']],expanded_research=[r['id'] for r in rows]),notes='6 FCC-sourced sites plus 7 explicitly synthetic regional positions anchored by gateway project evidence. Neither project announcement nor licensing proves current operation. Original catalogue is preserved.')
(root/'realdatas/OneWeb_research_gateways.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('OneWeb: 13 sites; 6 FCC coordinates + 7 regional simulation points')
