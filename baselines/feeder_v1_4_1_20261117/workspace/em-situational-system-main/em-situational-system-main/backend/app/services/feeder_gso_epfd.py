"""V1.4.1 spectral-window EPFD research reference (not regulatory certification)."""
import numpy as np
from .feeder_fast_interference import angles
from .feeder_interference import C,s1428,tx_pattern_at_frequency


def overlap_hz(carrier_centers, carrier_bandwidths, window_center, window_bandwidth):
    centers=np.asarray(carrier_centers,float);widths=np.asarray(carrier_bandwidths,float)
    if (not np.isfinite(window_center) or not np.isfinite(window_bandwidth) or window_bandwidth<=0
        or np.any(~np.isfinite(centers)) or np.any(~np.isfinite(widths)) or np.any(widths<=0)):
        raise ValueError('invalid spectral interval')
    low=np.maximum(centers-widths/2,window_center-window_bandwidth/2)
    high=np.minimum(centers+widths/2,window_center+window_bandwidth/2)
    return np.maximum(high-low,0), (low+high)/2


def epfd_windows(sources, targets, receivers, boresights, normals,
                 carrier_centers_hz, carrier_bandwidths_hz, tx_powers_w,
                 windows, diameters_m, tx_half_width_deg):
    """Each window={center_hz,bandwidth_hz}. Output [diameter,receiver,window,source].
    Flat rectangular PSD and ideal rectangular reference window. Gains evaluated
    at midpoint of each nonempty spectral intersection: narrow-window quadrature.
    No kTB, receiving business bandwidth or regulatory limits are assumed.
    """
    source=np.asarray(sources,float);target=np.asarray(targets,float)
    receiver=np.asarray(receivers,float);normal=np.asarray(normals,float)
    widths=np.broadcast_to(np.asarray(carrier_bandwidths_hz,float),(len(source),))
    powers=np.broadcast_to(np.asarray(tx_powers_w,float),(len(source),))
    diameters=np.asarray(diameters_m,float)
    if np.any(~np.isfinite(powers)) or np.any(powers<0) or np.any(~np.isfinite(diameters)) or np.any(diameters<=0):
        raise ValueError('invalid power or aperture')
    delta=source[None,:,:]-receiver[:,None,:];distance=np.linalg.norm(delta,axis=-1)
    tx_angle=angles(target[None,:,:]-source[None,:,:],-delta)
    rx_angle=angles(np.asarray(boresights)[:,None,:]-receiver[:,None,:],delta)
    visible=np.sum(delta*normal[:,None,:],axis=-1)>0
    shape=(len(diameters),len(receiver),len(windows),len(source))
    epfd=np.zeros(shape);received=np.zeros(shape);spectral=np.zeros((len(windows),len(source)))
    midpoint=np.zeros_like(spectral)
    for w,window in enumerate(windows):
        overlap,freq=overlap_hz(carrier_centers_hz,widths,window['center_hz'],window['bandwidth_hz'])
        spectral[w]=powers*overlap/widths;midpoint[w]=freq
        for i,j in zip(*np.where(visible&(overlap[None,:]>0))):
            f=float(freq[j])
            if not 10.7e9<=f<30e9:raise ValueError('frequency outside shared pattern domain')
            gt=10**(tx_pattern_at_frequency(float(tx_angle[i,j]),f,18.2e9,35,tx_half_width_deg,-20)/10)
            pfd=spectral[w,j]*gt/(4*np.pi*distance[i,j]**2)
            for d,diameter in enumerate(diameters):
                gr=10**(s1428(float(rx_angle[i,j]),diameter*f/C)/10)
                peak=10**(s1428(0,diameter*f/C)/10)
                epfd[d,i,w,j]=pfd*gr/peak
                received[d,i,w,j]=pfd*gr*(C/f)**2/(4*np.pi)
    return dict(epfd_w_m2_by_source=epfd,received_w_by_source=received,
                in_window_tx_power_w=spectral,intersection_midpoint_hz=midpoint,
                tx_offaxis_deg=tx_angle,rx_offaxis_deg=rx_angle,range_m=distance,visible=visible)
