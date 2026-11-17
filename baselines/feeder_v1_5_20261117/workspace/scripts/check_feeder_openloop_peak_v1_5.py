"""Independent scalar source-by-source audit of the largest 1m/40kHz peak."""
import gzip
import json
import math
import numpy as np
from run_feeder_openloop_v1_5 import ROOT, C, wgs84, dump, s1428, tx_pattern_at_frequency
from app.services.feeder_interference import angle


def main():
    out=ROOT/'results/feeder_openloop_v1_5'
    audit=json.loads((out/'completed_validation.json').read_text(encoding='utf-8'))
    peak=audit['epfd_peaks']['1m_40000Hz_combined'];frame=peak['frame'];window=peak['window']
    with gzip.open(out/f'input_{frame:03d}.json.gz','rt',encoding='utf-8') as f:inp=json.load(f)
    config=json.loads((out/'config.json').read_text(encoding='utf-8'))
    stations=json.loads((out/'stations.json').read_text(encoding='utf-8'))
    ground={g['id']:wgs84.latlon(g['latitude'],g['longitude'],elevation_m=g['altitude_m']).itrs_xyz.m for g in stations}
    receiver=next(r for r in inp['protected_links'] if r['gateway_id']==peak['receiver'])
    station=next(g for g in stations if g['id']==peak['receiver'])
    lat,lon=np.radians([station['latitude'],station['longitude']]);normal=np.array([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])
    pos={s:np.array(p) for s,p in inp['positions_ecef_m'].items()};g=ground[station['id']];boresight=pos[receiver['satellite_id']]-g
    contributions=[]
    for link,ch in zip(inp['links'],inp['channels']):
        center=17.85e9+1e8*ch;lo=max(center-5e7,window['center_hz']-window['bandwidth_hz']/2);hi=min(center+5e7,window['center_hz']+window['bandwidth_hz']/2)
        source=pos[link['satellite_id']];delta=source-g
        if hi<=lo or delta@normal<=0:continue
        f=(lo+hi)/2;distance=np.linalg.norm(delta)
        tx=angle(ground[link['gateway_id']]-source,g-source);rx=angle(boresight,delta)
        gt=tx_pattern_at_frequency(tx,f,18.2e9,35,config['model']['tx_half_width_deg'])
        gr=s1428(rx,f/C)-s1428(0,f/C)
        value=10**1.2*(hi-lo)/1e8*10**((gt+gr)/10)/(4*math.pi*distance**2)
        contributions.append(dict(link_id=link['link_id'],operator=link['constellation_id'],gateway_id=link['gateway_id'],channel=int(ch),tx_offaxis_deg=tx,rx_offaxis_deg=rx,range_km=distance/1000,tx_gain_dbi=gt,normalized_rx_gain_db=gr,epfd_w_m2=float(value)))
    total=sum(r['epfd_w_m2'] for r in contributions);value=10*math.log10(total)
    np.testing.assert_allclose(value,peak['dbw_m2'],rtol=0,atol=1e-10)
    contributions.sort(key=lambda r:-r['epfd_w_m2'])
    result=dict(status='passed',frame=frame,receiver=peak['receiver'],window=window,scalar_epfd_dbw_m2=value,expected_dbw_m2=peak['dbw_m2'],contributing_sources=len(contributions),dominant_source_fraction=contributions[0]['epfd_w_m2']/total,top_sources=contributions[:10])
    dump(out/'peak_scalar_validation.json',result);print(json.dumps(result))


if __name__=='__main__':main()
