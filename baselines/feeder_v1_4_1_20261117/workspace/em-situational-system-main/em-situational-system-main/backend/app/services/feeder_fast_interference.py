"""V1.4 rectangular NGSO/GSO reference and bounded screening kernels.
Research model only; all distances metres and powers Watts.
"""
from time import perf_counter
import math
import numpy as np
from .feeder_interference import C, s1428, tx_pattern_at_frequency


def angles(a,b):
    a,b=np.broadcast_arrays(np.asarray(a,float),np.asarray(b,float))
    if np.any(np.linalg.norm(a,axis=-1)==0) or np.any(np.linalg.norm(b,axis=-1)==0):
        raise ValueError('zero direction')
    return np.degrees(np.arctan2(np.linalg.norm(np.cross(a,b),axis=-1),np.sum(a*b,axis=-1)))


def compute(sources, targets, receivers, boresights, normals, frequencies,
            channels, receiver_channels, diameters, half_width,
            omission_budget_w=0., reference_frequency=18.2e9, desired_source_indices=None):
    """Rectangular rows=receivers columns=active NGSO transmitters.
    receiver_channels: -1 monitors all channels (GSO), else only own channel.
    Sources/targets are satellite ECEF and its serving gateway ECEF.
    Omitted upper bounds sum <= budget separately for each row AND channel.
    No actual omitted powers are used in screening. Kept contributions exact.
    """
    if not math.isfinite(omission_budget_w) or omission_budget_w<0:raise ValueError('invalid budget')
    t0=perf_counter();sources=np.asarray(sources,float);targets=np.asarray(targets,float)
    receivers=np.asarray(receivers,float);boresights=np.asarray(boresights,float)
    normals=np.asarray(normals,float);f=np.asarray(frequencies,float);ch=np.asarray(channels,int)
    rc=np.asarray(receiver_channels,int);diameters=np.asarray(diameters,float)
    if np.any(~np.isfinite(f)) or np.any((f<10.7e9)|(f>=30e9)) or np.any(diameters<=0):raise ValueError('invalid antenna inputs')
    delta=sources[None,:,:]-receivers[:,None,:];distance=np.linalg.norm(delta,axis=-1)
    rx_angle=angles(boresights[:,None,:]-receivers[:,None,:],delta)
    eligible=(np.sum(delta*normals[:,None,:],axis=-1)>0)&((rc[:,None]<0)|(rc[:,None]==ch[None,:]))
    if desired_source_indices is not None:
        for i,j in enumerate(desired_source_indices):
            if j>=0:eligible[i,j]=False
    geometry_seconds=perf_counter()-t0;t1=perf_counter()
    rx_gain=np.zeros(distance.shape)
    for i,j in zip(*np.where(eligible)):
        rx_gain[i,j]=s1428(float(rx_angle[i,j]),float(diameters[i]*f[j]/C))
    # TX envelope never exceeds peak for selected model/domain; reject if its
    # far/back floors or plateau could violate that assumption.
    peak=35+20*np.log10(f/reference_frequency)
    if np.any(peak<0):raise ValueError('TX peak bound invalid')
    factor=10**((12+rx_gain)/10)*(C/f[None,:]/(4*np.pi*distance))**2
    upper=factor*10**(peak[None,:]/10);upper[~eligible]=0
    rx_seconds=perf_counter()-t1;t2=perf_counter();keep=eligible.copy();bound=np.zeros((len(receivers),8))
    if omission_budget_w:
        for i in range(len(receivers)):
            for c in np.unique(ch):
                js=np.where(eligible[i]&(ch==c))[0]
                order=js[np.argsort(upper[i,js],kind='stable')]
                omitted=order[np.cumsum(upper[i,order])<=omission_budget_w]
                keep[i,omitted]=False;bound[i,c]=np.sum(upper[i,omitted])
    screening_seconds=perf_counter()-t2;t3=perf_counter()
    ii,jj=np.where(keep);tx_angle=angles(targets[jj]-sources[jj],receivers[ii]-sources[jj])
    power=np.zeros(distance.shape)
    for k,(i,j) in enumerate(zip(ii,jj)):
        gain=tx_pattern_at_frequency(float(tx_angle[k]),float(f[j]),reference_frequency,35,half_width,-20)
        power[i,j]=factor[i,j]*10**(gain/10)
    tx_seconds=perf_counter()-t3
    return dict(power_w=power,omitted_upper_w=bound,eligible_pairs=int(np.sum(eligible)),evaluated_pairs=len(ii),
                timings=dict(geometry_s=geometry_seconds,rx_pattern_s=rx_seconds,screening_s=screening_seconds,tx_pattern_s=tx_seconds,total_s=perf_counter()-t0))


def channel_sums(power,channels):
    return np.stack([np.sum(power[:,np.asarray(channels)==c],axis=1) for c in range(8)],axis=1)
