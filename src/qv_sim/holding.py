"""Ideal-information, fixed-association holding-period MILP (Gbit/s, Gbit)."""
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


def solve_period(link_steps, capacity_steps, flows, policy='qos', step_seconds=5,
                 fixed=None, free_association=False, objective_tolerance_gbit=1e-6):
    """Lexicographic per-GS volume deficits, then delivery.

    Association is chosen among links available at the first step and held even
    if that link disappears. free_association is a diagnostic relaxation only.
    Throughput uses total delivery first, then the same high/ordinary deficits.
    Capacity dictionaries may vary per step, allowing protected resources later.
    The objective tolerance is the maximum numerical slack in each stage lock.
    """
    if policy not in ('qos', 'throughput') or not link_steps or len(link_steps) != len(capacity_steps):
        raise ValueError('Invalid policy or horizon')
    if step_seconds <= 0 or not flows:
        raise ValueError('Invalid duration or flows')
    if not np.isfinite(objective_tolerance_gbit) or objective_tolerance_gbit < 0:
        raise ValueError('Invalid objective tolerance')
    if any(f.name not in ('high', 'ordinary') or not 0 <= f.minimum <= f.demand for f in flows):
        raise ValueError('Expected valid high/ordinary flows')
    if len({(f.gateway,f.name) for f in flows}) != len(flows):
        raise ValueError('Duplicate flow')
    for links,caps in zip(link_steps,capacity_steps):
        if any(not np.isfinite(v) or v < 0 for v in [*links.values(),*caps.values()]):
            raise ValueError('Invalid capacity')
        if any(s not in caps for _,s in links):
            raise ValueError('Missing satellite capacity')
    nt, nf = len(link_steps), len(flows)
    gateways = sorted({f.gateway for f in flows})
    initial = sorted(e for e in link_steps[0] if e[0] in gateways)
    # x is constant in the main model; diagnostic relaxation has per-step x.
    xkeys = [(t,e) for t,links in enumerate(link_steps) for e in sorted(links) if e[0] in gateways] if free_association else [(0,e) for e in initial]
    xi = {key:i for i,key in enumerate(xkeys)}
    ykeys = [(t,e) for t,links in enumerate(link_steps) for e in sorted(links)
             if (t if free_association else 0,e) in xi]
    yi = {key:len(xi)+i for i,key in enumerate(ykeys)}
    ro = len(xi)+len(yi); do = ro+nt*nf; size = do+nf
    lo = np.zeros(size); hi = np.full(size,np.inf); hi[:len(xi)] = 1
    for (t,e),i in xi.items():
        if fixed is not None:
            hi[i] = int(fixed.get(e[0]) == e[1])
    for (t,e),i in yi.items():
        hi[i] = link_steps[t][e]
    for t in range(nt):
        hi[ro+t*nf:ro+(t+1)*nf] = [f.demand for f in flows]
    target = np.array([f.minimum*step_seconds*nt for f in flows])
    hi[do:] = target
    rr=[];cc=[];vv=[];lower=[];upper=[]
    def add(entries, low=-np.inf, high=np.inf):
        row=len(lower)
        for col,value in entries:
            if value:
                rr.append(row);cc.append(col);vv.append(value)
        lower.append(low);upper.append(high)
    for t in (range(nt) if free_association else [0]):
        for g in gateways:
            add([(i,1) for (tt,e),i in xi.items() if tt==t and e[0]==g],high=1)
    for (t,e),i in yi.items():
        add([(i,1),(xi[t if free_association else 0,e],-link_steps[t][e])],high=0)
    for t in range(nt):
        for g in gateways:
            add([(i,1) for (tt,e),i in yi.items() if tt==t and e[0]==g]+
                [(ro+t*nf+k,-1) for k,f in enumerate(flows) if f.gateway==g],0,0)
        for s,cap in capacity_steps[t].items():
            add([(i,1) for (tt,e),i in yi.items() if tt==t and e[1]==s],high=cap)
    for k in range(nf):
        add([(ro+t*nf+k,step_seconds) for t in range(nt)]+[(do+k,1)],low=target[k])
    high = np.zeros(size); ordinary = np.zeros(size); delivery = np.zeros(size)
    for k,f in enumerate(flows):
        (high if f.name=='high' else ordinary)[do+k] = 1
    delivery[ro:do] = -step_seconds
    objectives = [high,ordinary,delivery] if policy=='qos' else [delivery,high,ordinary]
    optima=[]
    for objective in objectives:
        matrix=coo_matrix((vv,(rr,cc)),shape=(len(lower),size)).tocsc()
        result=milp(objective,integrality=np.r_[np.ones(len(xi)),np.zeros(size-len(xi))],
                    bounds=Bounds(lo,hi),constraints=LinearConstraint(matrix,lower,upper),
                    options={'mip_rel_gap':0.0,'time_limit':120})
        if not result.success:
            raise RuntimeError(f'Period MILP stage {len(optima) + 1} not optimal: {result.message}')
        value=float(objective@result.x);optima.append(value)
        add([(i,v) for i,v in enumerate(objective) if v],high=value+objective_tolerance_gbit)
    rates=result.x[ro:do].reshape(nt,nf)
    volumes=step_seconds*rates.sum(axis=0)
    deficits=np.maximum(0,target-volumes)
    associations=[{g:s for (tt,(g,s)),i in xi.items() if tt==(t if free_association else 0) and result.x[i]>.5} for t in range(nt)]
    return {'association':associations[0], 'associations':associations,
            'rates':rates.tolist(),'volumes':volumes.tolist(),'deficits':deficits.tolist(),
            'high_deficit_gbit':float(sum(d for f,d in zip(flows,deficits) if f.name=='high')),
            'ordinary_deficit_gbit':float(sum(d for f,d in zip(flows,deficits) if f.name=='ordinary')),
            'total_gbit':float(volumes.sum()),'lexicographic_optima':optima}
