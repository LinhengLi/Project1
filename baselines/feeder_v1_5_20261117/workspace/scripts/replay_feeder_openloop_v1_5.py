"""Recompute a saved input without propagation, selection or random decisions."""
import argparse
import gzip
import json
from pathlib import Path
from time import perf_counter
import numpy as np
from run_feeder_openloop_v1_5 import ROOT, C, K, wgs84, exact_ngso, epfd_windows, dump


def main():
    p=argparse.ArgumentParser();p.add_argument('--frame',type=int,required=True);p.add_argument('--source',default='results/feeder_openloop_v1_5');p.add_argument('--out',required=True);args=p.parse_args()
    source=ROOT/args.source;out=ROOT/args.out;out.mkdir(parents=True,exist_ok=False)
    config=json.loads((source/'config.json').read_text(encoding='utf-8'));model=config['model']
    stations=json.loads((source/'stations.json').read_text(encoding='utf-8'))
    with gzip.open(source/f'input_{args.frame:03d}.json.gz','rt',encoding='utf-8') as f:inp=json.load(f)
    expected=json.loads((source/f'result_{args.frame:03d}.json').read_text(encoding='utf-8'))
    ground={};normal={}
    for g in stations:
        ground[g['id']]=wgs84.latlon(g['latitude'],g['longitude'],elevation_m=g['altitude_m']).itrs_xyz.m
        lat,lon=np.radians([g['latitude'],g['longitude']]);normal[g['id']]=[np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)]
    links=inp['links'];protected=inp['protected_links'];channels=np.array(inp['channels']);pos=inp['positions_ecef_m']
    start=perf_counter()
    ng=exact_ngso(links,pos,ground,normal,channels,model['tx_half_width_deg'],model['rx_diameter_m'])
    gs=epfd_windows(sources=[pos[r['satellite_id']] for r in links],targets=[ground[r['gateway_id']] for r in links],receivers=[ground[r['gateway_id']] for r in protected],boresights=[pos[r['satellite_id']] for r in protected],normals=[normal[r['gateway_id']] for r in protected],carrier_centers_hz=17.85e9+1e8*channels,carrier_bandwidths_hz=model['bandwidth_hz'],tx_powers_w=10**(model['tx_dbw']/10),windows=model['windows'],diameters_m=model['diameters_m'],tx_half_width_deg=model['tx_half_width_deg'])
    mask=channels[:,None]==channels[None,:];np.fill_diagonal(mask,False)
    ratio=(ng*mask).sum(axis=1)/(K*model['noise_k']*model['bandwidth_hz'])
    failed=[r['link_id'] for r,v in zip(links,ratio) if v>10**(model['threshold_db']/10)]
    elapsed=perf_counter()-start
    assert failed==expected['failed_link_ids']
    for i,v in enumerate(expected['in_db']):
        if v is None:assert ratio[i]==0
        else:np.testing.assert_allclose(10*np.log10(ratio[i]),v,atol=1e-10,rtol=0)
    operators=np.array([r['constellation_id'] for r in links]);ep=gs['epfd_w_m2_by_source']
    systems=np.stack([ep[:,:,:,operators==op].sum(axis=-1) for op in ['starlink','oneweb']]+[ep.sum(axis=-1)],axis=-1)
    for b,bw in enumerate([4e4,1e6]):
        js=[i for i,w in enumerate(model['windows']) if w['bandwidth_hz']==bw]
        peaks=systems[:,:,js,:].max(axis=2)
        expected_peak=np.array(expected['epfd_peaks_db'][b],dtype=float)
        np.testing.assert_array_equal(np.isnan(expected_peak),peaks==0)
        valid=peaks>0;np.testing.assert_allclose(10*np.log10(peaks[valid]),expected_peak[valid],rtol=0,atol=1e-10)
    np.savez_compressed(out/'matrices.npz',ngso_power_w=ng,**gs)
    result=dict(status='passed',frame=args.frame,active_links=len(links),failed=len(failed),recompute_wall_s=elapsed,scope='same saved input, no propagation/selection/random generation; includes aggregate and validation input preparation as documented')
    dump(out/'validation.json',result);print(json.dumps(result))


if __name__=='__main__':main()
