"""Single-slot MILP. All rates are Gbit/s; no end-to-end or delay claims."""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


@dataclass(frozen=True)
class Flow:
    gateway: str
    name: str
    demand: float
    minimum: float
    weight: float


def solve(links, satellite_capacity, flows, policy, fixed=None):
    """Lexicographic throughput/QoS objectives, optimality required.

    links: {(gateway, satellite): rate}. QoS cost = sum(weight * deficit).
    Independent association uses rate then satellite ID as deterministic tie-break.
    """
    if policy not in ('independent', 'throughput', 'qos'):
        raise ValueError('Unknown policy')
    if not flows or any(not 0 <= f.minimum <= f.demand or f.weight <= 0 for f in flows):
        raise ValueError('Invalid flows')
    if any(not np.isfinite(v) or v < 0 for v in [*links.values(), *satellite_capacity.values()]):
        raise ValueError('Invalid capacity')
    if any(s not in satellite_capacity for _,s in links):
        raise ValueError('Missing satellite capacity')
    edges = sorted(links)
    ne, nf = len(edges), len(flows)
    # x edge binary; y edge continuous rate; r flow rate; d flow deficit
    size = 2*ne+2*nf
    lo = np.zeros(size); hi = np.full(size,np.inf)
    hi[:ne] = 1
    hi[ne:2*ne] = [links[e] for e in edges]
    hi[2*ne:2*ne+nf] = [f.demand for f in flows]
    hi[2*ne+nf:] = [f.minimum for f in flows]
    gateways = sorted({f.gateway for f in flows} | {g for g,_ in edges})
    if policy == 'independent' and fixed is None:
        fixed = {g: min((e for e in edges if e[0]==g),key=lambda e:(-links[e],e[1]))[1]
                 for g in gateways if any(e[0]==g for e in edges)}
    if fixed is not None:
        for i,(g,s) in enumerate(edges):
            hi[i] = int(fixed.get(g)==s)
    rows=[]; lower=[]; upper=[]
    def add(entries, low=-np.inf, high=np.inf):
        row=np.zeros(size)
        for i,value in entries: row[i]+=value
        rows.append(row);lower.append(low);upper.append(high)
    for g in gateways:
        add([(i,1) for i,e in enumerate(edges) if e[0]==g],high=1)
        add([(ne+i,1) for i,e in enumerate(edges) if e[0]==g]+
            [(2*ne+k,-1) for k,f in enumerate(flows) if f.gateway==g],0,0)
    for i,e in enumerate(edges): add([(ne+i,1),(i,-links[e])],high=0)
    for s,cap in satellite_capacity.items():
        add([(ne+i,1) for i,e in enumerate(edges) if e[1]==s],high=cap)
    for k,f in enumerate(flows): add([(2*ne+k,1),(2*ne+nf+k,1)],low=f.minimum)
    throughput=np.zeros(size);throughput[2*ne:2*ne+nf]=-1
    qos=np.zeros(size);qos[2*ne+nf:]=[f.weight for f in flows]
    def run(objective):
        result=milp(objective,integrality=np.r_[np.ones(ne),np.zeros(size-ne)],
                    bounds=Bounds(lo,hi),constraints=LinearConstraint(np.array(rows),lower,upper),
                    options={'mip_rel_gap':0.0,'time_limit':60})
        if not result.success: raise RuntimeError(f'MILP not optimal: {result.message}')
        return result
    first = throughput if policy=='throughput' else qos
    second = qos if policy=='throughput' else throughput
    a=run(first)
    add(list(enumerate(first)),high=float(first@a.x)+1e-7)
    b=run(second)
    rates=b.x[2*ne:2*ne+nf]
    deficits=np.maximum(0,np.array([f.minimum for f in flows])-rates)
    association={g:s for i,(g,s) in enumerate(edges) if b.x[i]>.5}
    # Compute metrics from achieved rates, not slack variables.
    denominator=sum(f.weight*f.minimum for f in flows)
    return {'association':association,'rates':rates.tolist(),'throughput':float(rates.sum()),
            'weighted_deficit':float(sum(f.weight*d for f,d in zip(flows,deficits))),
            'normalized_weighted_deficit':float(sum(f.weight*d for f,d in zip(flows,deficits))/denominator) if denominator else 0,
            'flow_violation_fraction':float(np.mean(deficits>1e-5)),
            'satellite_load':{s:float(sum(b.x[ne+i] for i,e in enumerate(edges) if e[1]==s)) for s in satellite_capacity}}
