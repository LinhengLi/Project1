"""Derived v1.2 research physics; metres, degrees, Hz, Watts throughout."""
import math
import numpy as np

C = 299792458.0
K = 1.380649e-23


def angle(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if not np.all(np.isfinite([a,b])) or min(np.linalg.norm(a), np.linalg.norm(b)) == 0:
        raise ValueError('invalid direction')
    return math.degrees(math.atan2(np.linalg.norm(np.cross(a,b)), np.dot(a,b)))


def s1528(theta, peak, half_width, sidelobe=-20):
    """S.1528-0 1.2 circular z=1 only; based on user-confirmed audit report."""
    if not 0 <= theta <= 180 or half_width <= 0 or sidelobe not in (-15,-20,-25,-30):
        raise ValueError('invalid S.1528 parameters')
    a,b=2.58,6.32
    y=b*half_width*10**(.04*(peak+sidelobe))
    if y > 90 or a*half_width > 90:
        raise ValueError('unsupported overlapping pattern regions')
    if theta <= a*half_width:return peak-3*(theta/half_width)**1.5
    if theta <= b*half_width:return peak+sidelobe
    if theta <= y:return peak+sidelobe-25*math.log10(theta/(b*half_width))
    if theta <= 90:return 0.0
    return max(15+sidelobe+.25*peak,0)


def tx_pattern_at_frequency(theta, frequency_hz, reference_frequency_hz,
                            peak_dbi, half_width_deg, sidelobe=-20):
    """Fixed effective aperture and efficiency; reference model, not measured hardware."""
    if not all(math.isfinite(v) and v > 0 for v in
               (frequency_hz, reference_frequency_hz, half_width_deg)):
        raise ValueError('invalid frequency or width')
    ratio=frequency_hz/reference_frequency_hz
    return s1528(theta, peak_dbi+20*math.log10(ratio), half_width_deg/ratio, sidelobe)


def s1428(theta, q):
    if not 0 <= theta <= 180 or not math.isfinite(q) or q < 20:
        raise ValueError('outside S.1428 domain')
    peak=20*math.log10(q)+(7.7 if q<=100 else 8.4)
    g1=29-25*math.log10(95/q) if q<=100 else -1+15*math.log10(q)
    m=20/q*math.sqrt(peak-g1)
    r=95/q if q<=100 else 15.85*q**(-.6)
    if theta < m:return peak-.0025*(q*theta)**2
    if theta < r:return g1
    if q<=100:
        if theta<=33.1:return 29-25*math.log10(theta)
        if theta<=80:return -9.0
        if q<=25:return -5.0
        return -4.0 if theta<=120 else -9.0
    if theta<10:return 29-25*math.log10(theta)
    if theta<34.1:return 34-30*math.log10(theta)
    if theta<80:return -12.0
    return -7.0 if theta<120 else -12.0


def matrix(links, satellites, grounds, normals, frequency_hz, tx_half_width_deg,
           rx_diameter_m, tx_peak=35., tx_dbw=12., sidelobe=-20,
           tx_reference_frequency_hz=None):
    """Rows victim i, columns transmitter j. Diagonal is desired signal.
    Exclude sources at/below local WGS84 tangent horizon. No 40deg interference cutoff.
    """
    frequencies=np.broadcast_to(np.asarray(frequency_hz,float),(len(links),))
    if np.any(~np.isfinite(frequencies)) or np.any((frequencies<10.7e9)|(frequencies>=30e9)):raise ValueError('frequency outside common scope')
    n=len(links); power=np.zeros((n,n)); tx=np.zeros((n,n)); rx=np.zeros((n,n)); distance=np.zeros((n,n))
    for i,v in enumerate(links):
        g=np.asarray(grounds[v['gateway_id']]); own=np.asarray(satellites[v['satellite_id']])
        for j,s in enumerate(links):
            f=float(frequencies[j])
            p=np.asarray(satellites[s['satellite_id']]); target=np.asarray(grounds[s['gateway_id']]); delta=p-g
            d=float(np.linalg.norm(delta)); distance[i,j]=d
            tx[i,j]=angle(target-p,g-p); rx[i,j]=angle(own-g,delta)
            if np.dot(delta,normals[v['gateway_id']])<=0:continue
            tx_gain=(s1528(tx[i,j],tx_peak,tx_half_width_deg,sidelobe)
                     if tx_reference_frequency_hz is None else
                     tx_pattern_at_frequency(tx[i,j],f,tx_reference_frequency_hz,tx_peak,tx_half_width_deg,sidelobe))
            gain=tx_gain+s1428(rx[i,j],rx_diameter_m*f/C)
            power[i,j]=10**((tx_dbw+gain)/10)*(C/f/(4*math.pi*d))**2
    return dict(received_power_w=power,tx_offaxis_deg=tx,rx_offaxis_deg=rx,range_m=distance)


def aggregate(power, links, channels, bandwidth_hz=1e8, temperature_k=398., threshold_db=-12.2):
    if len(channels)!=len(links) or bandwidth_hz<=0 or temperature_k<=0:raise ValueError('invalid receiver inputs')
    categories={k:np.zeros(len(links)) for k in ('intra_gateway','same_operator_inter_gateway','cross_operator')}
    for i,v in enumerate(links):
        for j,s in enumerate(links):
            if i==j or channels[i]!=channels[j]:continue
            key='intra_gateway' if v['gateway_id']==s['gateway_id'] else ('same_operator_inter_gateway' if v['constellation_id']==s['constellation_id'] else 'cross_operator')
            categories[key][i]+=power[i,j]
    total=sum(categories.values()); noise=K*temperature_k*bandwidth_hz
    return dict(category_power_w={k:v.tolist() for k,v in categories.items()},aggregate_power_w=total.tolist(),noise_w=noise,in_linear=(total/noise).tolist(),lf_rate=float(np.mean(total/noise>10**(threshold_db/10))) if len(links) else None)
