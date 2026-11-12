"""Paired 50 GHz feeder experiment with a per-station emission limit."""
import argparse
import csv
import gzip
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

from qv_sim.atmosphere import gaseous_loss_db
from qv_sim.holding import solve_period
from qv_sim.sharing import Flow
from qv_sim.spectrum import (
    fss_mask_suppression_db,
    integrated_suppression_db,
    link_budget,
    link_capacity_gbps,
    port_power_budget,
)
from experiment_lookahead import write_csv
from experiment_temporal import metrics


OBJECTIVE_TOLERANCE_GBIT = 1e-4


def load_geometry(frozen):
    source = Path(frozen['source'])
    if hashlib.sha256(source.read_bytes()).hexdigest() != frozen['sha256']:
        raise ValueError('Frozen candidate source hash changed')
    step = frozen['step_seconds']
    windows = {}
    for name, window in frozen['windows'].items():
        start = datetime.fromisoformat(window['start'])
        end = datetime.fromisoformat(window['end_exclusive'])
        duration = (end - start).total_seconds()
        if duration <= 0 or duration % step:
            raise ValueError('Expected a nonempty window with complete steps')
        windows[name] = [start + timedelta(seconds=i) for i in range(0, int(duration), step)]
    geometry = {time: {} for times in windows.values() for time in times}
    with gzip.open(source, 'rt', encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            time = datetime.fromisoformat(row['utc'])
            if time in geometry:
                edge = (row['station_id'], row['norad_id'])
                geometry[time][edge] = (float(row['range_km']), float(row['elevation_deg']),
                                        float(row['capacity_loss10_gbps']))
    if any(not edges for edges in geometry.values()):
        raise ValueError('Missing frozen candidate snapshot')
    return windows, geometry


def build_capacities(windows, geometry, budget, emission, gas_losses=None):
    slots = {}
    capacity_rows = []
    capacity_summary = []
    for suppression in emission['suppression_db']:
        nominal = port_power_budget(emission['nominal_eirp_dbw'], emission['antenna_gain_dbi'],
                                    suppression)
        limited = port_power_budget(emission['nominal_eirp_dbw'], emission['antenna_gain_dbi'],
                                    suppression, emission['limit_dbw'])
        if limited['leakage_dbw'] > emission['limit_dbw'] + 1e-9:
            raise RuntimeError('Protected antenna-port leakage exceeds its limit')
        for scenario, times in windows.items():
            before = {}
            after = {}
            losses = []
            for time in times:
                before[time] = {}
                after[time] = {}
                for edge, (distance, elevation, _) in geometry[time].items():
                    gas = 0 if gas_losses is None else gas_losses[time, edge]
                    edge_budget = dict(budget, extra_loss_db=budget['extra_loss_db'] + gas)
                    nominal_budget = link_budget(distance, eirp_dbw=nominal['eirp_dbw'], **edge_budget)
                    limited_budget = link_budget(distance, eirp_dbw=limited['eirp_dbw'], **edge_budget)
                    off = nominal_budget['capacity_gbps']
                    on = limited_budget['capacity_gbps']
                    if on > off or (limited['backoff_db'] == 0 and on != off):
                        raise RuntimeError('Invalid protected capacity')
                    before[time][edge], after[time][edge] = off, on
                    losses.append(off - on)
                    capacity_rows.append({
                        'scenario': scenario, 'suppression_db': suppression, 'utc': time.isoformat(),
                        'gateway': edge[0], 'satellite': edge[1], 'range_km': distance,
                        'elevation_deg': elevation, 'fspl_db': nominal_budget['fspl_db'],
                        'gaseous_loss_db': gas, 'other_loss_db': budget['extra_loss_db'],
                        'eirp_off_dbw': nominal['eirp_dbw'], 'eirp_on_dbw': limited['eirp_dbw'],
                        'effective_snr_off_db': nominal_budget['effective_snr_db'],
                        'effective_snr_on_db': limited_budget['effective_snr_db'],
                        'capacity_off_gbps': off,
                        'capacity_on_gbps': on, 'capacity_loss_gbps': off - on,
                    })
            slots[scenario, suppression, 'off'] = before
            slots[scenario, suppression, 'on'] = after
            capacity_summary.append({
                'scenario': scenario, 'suppression_db': suppression, **limited,
                'candidate_edge_steps': len(losses),
                'power_limited_edge_steps': len(losses) if limited['backoff_db'] > 0 else 0,
                'capacity_reduced_edge_steps': sum(loss > 1e-9 for loss in losses),
                'mean_capacity_loss_gbps': sum(losses) / len(losses),
                'max_capacity_loss_gbps': max(losses),
            })
    return slots, capacity_rows, capacity_summary


def evaluate(times, slots, gateways, load, policy, period, step, satellite_capacity, minimums):
    flows = [Flow(gateway, name, load, minimums[name], 1)
             for gateway in gateways for name in ('high', 'ordinary')]
    n = period // step
    rows, periods = [], []
    previous = {}
    for start in range(0, len(times), n):
        times_in_period = times[start:start + n]
        links = [slots[time] for time in times_in_period]
        capacities = [{s: satellite_capacity for _, s in edges} for edges in links]
        try:
            result = solve_period(links, capacities, flows, policy, step_seconds=step,
                                  objective_tolerance_gbit=OBJECTIVE_TOLERANCE_GBIT)
        except RuntimeError as error:
            raise RuntimeError(f'{policy} period starting {times_in_period[0]}: {error}') from error
        association = result['association']
        for k, time in enumerate(times_in_period):
            for j, gateway in enumerate(gateways):
                satellite = association.get(gateway, '')
                rows.append({
                    'utc': time.isoformat(), 'gateway': gateway, 'satellite': satellite,
                    'high': result['rates'][k][2*j], 'ordinary': result['rates'][k][2*j+1],
                    'switch': int(k == 0 and start > 0 and previous.get(gateway, '') != satellite),
                    'invalid_link': int(bool(satellite) and (gateway, satellite) not in links[k]),
                })
        for j, gateway in enumerate(gateways):
            periods.append({
                'start': times_in_period[0].isoformat(), 'gateway': gateway,
                'satellite': association.get(gateway, ''), 'high_gbit': result['volumes'][2*j],
                'ordinary_gbit': result['volumes'][2*j+1],
                'high_deficit_gbit': result['deficits'][2*j],
                'ordinary_deficit_gbit': result['deficits'][2*j+1],
            })
        previous = association
    summary = {
        'high_deficit_gbit': sum(row['high_deficit_gbit'] for row in periods),
        'ordinary_deficit_gbit': sum(row['ordinary_deficit_gbit'] for row in periods),
        'aligned_high_attainment': sum(row['high_deficit_gbit'] <= OBJECTIVE_TOLERANCE_GBIT + 1e-6
                                       for row in periods) / len(periods),
        'rolling_60_high_attainment': metrics(rows, gateways, 60)['high_attainment'],
        **metrics(rows, gateways, 30),
    }
    return summary, rows, periods


def paired_effects(summary):
    lookup = {(r['scenario'], r['suppression_db'], r['load'], r['protection'], r['policy']): r
              for r in summary}
    paired = []
    for (scenario, suppression, load, protection, policy), row in lookup.items():
        if protection != 'on' or policy != 'qos':
            continue
        off_qos = lookup[scenario, suppression, load, 'off', 'qos']
        on_throughput = lookup[scenario, suppression, load, 'on', 'throughput']
        off_throughput = lookup[scenario, suppression, load, 'off', 'throughput']
        paired.append({
            'scenario': scenario, 'suppression_db': suppression, 'load': load,
            'throughput_protection_added_high_deficit_gbit':
                on_throughput['high_deficit_gbit'] - off_throughput['high_deficit_gbit'],
            'qos_protection_added_high_deficit_gbit':
                row['high_deficit_gbit'] - off_qos['high_deficit_gbit'],
            'protected_qos_high_deficit_reduction_gbit':
                on_throughput['high_deficit_gbit'] - row['high_deficit_gbit'],
            'protected_qos_rolling_30_gain_pp':
                100 * (row['high_attainment'] - on_throughput['high_attainment']),
            'protected_qos_ordinary_delivery_change_gbit':
                row['ordinary_gbit'] - on_throughput['ordinary_gbit'],
            'protected_qos_total_delivery_change_gbit':
                row['total_gbit'] - on_throughput['total_gbit'],
            'protected_qos_longest_under_change_seconds':
                row['longest_under_seconds'] - on_throughput['longest_under_seconds'],
        })
    return paired


def write_report(path, capacities, paired, propagation, emission, gas_losses):
    refined = propagation['model'] != 'fixed'
    lines = [
        '# 50 GHz 馈电上行发射限值配对实验', '',
        '两个冻结窗口均为 120 秒。保护开／关都使用 50.0 GHz、250 MHz 和同一几何。',
        '抑制度是天线端口带内总功率与 50.2–50.4 GHz 积分泄漏功率之差。',
        '按 Resolution 750 所选情形，打开保护时施加 −42 dBW / 200 MHz 端口限值。',
        '采用固定谱形与固定发射功率设定。前瞻调度读取已保存的未来状态。',
        f'本轮词典序目标锁定容差为 {OBJECTIVE_TOLERANCE_GBIT:g} Gbit。', '',
    ]
    if refined:
        lines.extend([
            '## 模型输入', '',
            f"按 P.676-13 附录 1 和 P.835-7 参考大气计算，逐边气体衰减为 "
            f"{min(gas_losses.values()):.3f}–{max(gas_losses.values()):.3f} dB。",
            f"另外设置 {propagation['other_loss_db']:g} dB 余量。沿用冻结几何的站高，"
            '以几何仰角近似地面视仰角。',
            '保留旧抑制度扫描作受控比较。另将 SM.1541 通用 FSS 掩模积分为独立包络情景，'
            '以平坦带内谱和单信道指配为假设。',
            f"通用掩模包络的积分抑制度为 {emission['fss_mask_suppression_db']:.4f} dB。"
            '它用于检查包络情景的边界，设备实际泄漏需要独立数据。', '',
        ])
        if 'port_spectrum' in emission:
            lines.extend([f"输入端口谱的积分抑制度为 {emission['port_spectrum']['suppression_db']:.6g} dB。"
                          '将谱形归一到同一标称端口功率后比较。', ''])
    else:
        lines.extend(['抑制度采用合成假设，额外链路损耗沿用固定 10 dB。', ''])
    lines.extend([
        '## 发射功率与容量', '',
        '|场景|抑制度 dB|基准泄漏 dBW|保护后泄漏 dBW|回退 dB|容量下降边步数/总数|平均降幅 Gbit/s|最大降幅 Gbit/s|',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ])
    for r in capacities:
        lines.append(
            f"|{r['scenario']}|{r['suppression_db']:.6g}|{r['nominal_leakage_dbw']:.1f}|"
            f"{r['leakage_dbw']:.1f}|{r['backoff_db']:.1f}|"
            f"{r['capacity_reduced_edge_steps']}/{r['candidate_edge_steps']}|"
            f"{r['mean_capacity_loss_gbps']:.4f}|{r['max_capacity_loss_gbps']:.4f}|"
        )
    lines.extend([
        '', '平均降幅按全部候选边步计算。功率受限后，频谱效率封顶的部分边仍可保持容量。', '',
        '## 业务配对效应', '',
        '缺口为八站四周期的高优先级正缺口之和，单位 Gbit。交付量差值为 QoS 优先减去吞吐量优先。',
        '完整四组水平值、对齐和滚动达标率、切换及最长欠速见 summary.csv。', '',
        '|场景|抑制度 dB|每类负载 Gbit/s|保护新增缺口（吞吐优先）|保护新增缺口（QoS 优先）|保护下 QoS 减少缺口|滚动 30s 达标变化 pp|普通交付变化 Gbit|总交付变化 Gbit|最长欠速变化 s|',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ])
    for r in paired:
        throughput_loss = r['throughput_protection_added_high_deficit_gbit']
        qos_loss = r['qos_protection_added_high_deficit_gbit']
        qos_gain = r['protected_qos_high_deficit_reduction_gbit']
        throughput_loss = 0.0 if abs(throughput_loss) <= OBJECTIVE_TOLERANCE_GBIT else throughput_loss
        qos_loss = 0.0 if abs(qos_loss) <= OBJECTIVE_TOLERANCE_GBIT else qos_loss
        qos_gain = 0.0 if abs(qos_gain) <= OBJECTIVE_TOLERANCE_GBIT else qos_gain
        lines.append(
            f"|{r['scenario']}|{r['suppression_db']:.6g}|{r['load']}|"
            f"{throughput_loss:.3f}|{qos_loss:.3f}|{qos_gain:.3f}|"
            f"{r['protected_qos_rolling_30_gain_pp']:+.2f}|"
            f"{r['protected_qos_ordinary_delivery_change_gbit']:+.3f}|"
            f"{r['protected_qos_total_delivery_change_gbit']:+.3f}|"
            f"{r['protected_qos_longest_under_change_seconds']:+d}|"
        )
    lines.extend([
        '', '吞吐优先的新增高优缺口可为负。限值改变了最大吞吐量对应的关联与分配，'
        '其高优缺口属于次级目标。最小可达高优缺口应看以该缺口为首要目标的 QoS 方案。',
        '', '本实验只评估单发射端口限值情景。抑制度与天线增益需用设备资料校准，'
        '传感器接收端的聚合干扰、真实授权和端到端网络性能属于另外的测量问题。',
        '依据及后续参数见 [频谱保护资料](../../research_sources/spectrum_protection.md)。',
    ])
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refined', action='store_true', help='Use ITU reference gas loss and the FSS mask case')
    parser.add_argument('--residual-loss-db', type=float, default=0.0, help='Additional loss in refined runs')
    parser.add_argument('--port-spectrum', type=Path,
                        help='Optional antenna-port CSV with frequency_hz and psd_w_per_hz')
    args = parser.parse_args()
    if (not 0 <= args.residual_loss_db < float('inf')
            or (not args.refined and (args.port_spectrum is not None or args.residual_loss_db))):
        parser.error('Spectrum and finite nonnegative residual loss require --refined')
    holding = json.loads(Path('results/holding_qos/config.json').read_text(encoding='utf-8'))
    frozen = holding['frozen_input']
    refinement = json.loads(Path('results/real_gateway_refinement/config.json').read_text(encoding='utf-8'))
    previous_budget = refinement['budget']
    budget = {key: previous_budget[key] for key in ('bandwidth_hz', 'satellite_gt_db_per_k',
                                                   'implementation_gap_db', 'spectral_efficiency_cap')}
    budget.update(frequency_ghz=50.0, extra_loss_db=10.0)
    emission = {
        'active_band_ghz': [49.7, 50.2], 'passive_band_ghz': [50.2, 50.4],
        'limit_dbw': -42.0, 'nominal_eirp_dbw': previous_budget['gs_eirp_dbw'],
        'antenna_gain_dbi': 55.0, 'suppression_db': [55, 52, 51, 49, 46],
        'assumptions': 'Post-WRC-19 non-GSO fixed earth station, clear-sky rule, no uplink power control. '
                       'Antenna gain and integrated suppression are synthetic. Port reference absorbs feeder losses.',
    }
    windows, geometry = load_geometry(frozen)
    old_budget = dict(budget, frequency_ghz=previous_budget['frequency_ghz'])
    error_48 = max(abs(link_capacity_gbps(distance, eirp_dbw=emission['nominal_eirp_dbw'],
                                          **old_budget) - recorded)
                   for edges in geometry.values() for distance, _, recorded in edges.values())
    if error_48 > 1e-6:
        raise RuntimeError('Link budget does not reproduce the frozen 48 GHz capacities')
    gas_losses = None
    propagation = {'model': 'fixed', 'other_loss_db': budget['extra_loss_db']}
    if args.refined:
        station_height_km = refinement['source_scan']['altitude_assumption_m'] / 1000
        propagation = {'model': 'P.676-13 Annex 1 / P.835-7 Annex 1 / P.453-14',
                       'station_height_km': station_height_km, 'other_loss_db': args.residual_loss_db,
                       'elevation': 'Frozen geometric ground elevation used as apparent elevation'}
        budget['extra_loss_db'] = args.residual_loss_db
        gas_losses = {(time, edge): gaseous_loss_db(budget['frequency_ghz'], elevation, station_height_km)
                      for time, edges in geometry.items() for edge, (_, elevation, _) in edges.items()}
        centre_hz = budget['frequency_ghz'] * 1e9
        bandwidth = budget['bandwidth_hz']
        occupied_hz = [centre_hz - bandwidth/2, centre_hz + bandwidth/2]
        protected_hz = [frequency * 1e9 for frequency in emission['passive_band_ghz']]
        suppression = fss_mask_suppression_db(centre_hz, occupied_hz[1], bandwidth, protected_hz)
        emission['fss_mask_suppression_db'] = suppression
        emission['fss_mask_assigned_and_occupied_band_hz'] = occupied_hz
        emission['suppression_db'].append(suppression)
        if args.port_spectrum:
            with args.port_spectrum.open(encoding='utf-8-sig', newline='') as stream:
                samples = list(csv.DictReader(stream))
            suppression = integrated_suppression_db(
                [float(sample['frequency_hz']) for sample in samples],
                [float(sample['psd_w_per_hz']) for sample in samples], occupied_hz, protected_hz)
            emission['port_spectrum'] = {
                'path': str(args.port_spectrum), 'suppression_db': suppression,
                'sha256': hashlib.sha256(args.port_spectrum.read_bytes()).hexdigest(),
            }
            if suppression not in emission['suppression_db']:
                emission['suppression_db'].append(suppression)
    step, period = frozen['step_seconds'], holding['period_seconds']
    # The shared rolling metrics use a 5 s step and the existing 0.5 Gbit/s threshold.
    minimums = {name: volume / period for name, volume in holding['targets_gbit'].items()}
    if step != 5 or minimums['high'] != .5 or period % step or any(
            len(times) * step % period for times in windows.values()):
        raise ValueError('Expected the frozen step, high-rate target and complete holding periods')
    gateways = sorted(site['station_id'] for site in json.loads(
        Path('realdatas/gateway_main_8.json').read_text(encoding='utf-8'))['sites'])
    slots, capacity_rows, capacity_summary = build_capacities(windows, geometry, budget, emission, gas_losses)
    # With this homogeneous radio setup, larger suppression cannot reduce a protected capacity.
    for scenario, times in windows.items():
        levels = sorted(emission['suppression_db'])
        for lower, higher in zip(levels, levels[1:]):
            low = slots[scenario, lower, 'on']
            high = slots[scenario, higher, 'on']
            if any(low[t][e] > high[t][e] for t in times for e in low[t]):
                raise RuntimeError('Capacity decreased as leakage suppression increased')
    summary, traces, periods = [], [], []
    cache = {}
    backoffs = {(r['scenario'], r['suppression_db']): r['backoff_db'] for r in capacity_summary}
    for (scenario, suppression, protection), matrix in slots.items():
        backoff = backoffs[scenario, suppression] if protection == 'on' else 0
        for load in holding['load_per_class_gbps']:
            for policy in ('throughput', 'qos'):
                key = (scenario, backoff, load, policy)
                if key not in cache:
                    cache[key] = evaluate(windows[scenario], matrix, gateways, load, policy, period,
                                          step, frozen['satellite_capacity_gbps'], minimums)
                result, rows, station_periods = cache[key]
                tag = dict(scenario=scenario, suppression_db=suppression, protection=protection,
                           load=load, policy=policy)
                summary.append(dict(tag, **result))
                traces.extend(dict(tag, **r) for r in rows)
                periods.extend(dict(tag, **r) for r in station_periods)
    paired = paired_effects(summary)
    out = Path('results/spectrum_refined' if args.refined else 'results/spectrum_protection')
    out.mkdir(parents=True, exist_ok=True)
    config = {
        'frozen_input': frozen, 'budget': budget, 'emission': emission, 'step_seconds': step,
        'period_seconds': period, 'targets_gbit': holding['targets_gbit'],
        'load_per_class_gbps': holding['load_per_class_gbps'],
        'satellite_capacity_gbps': frozen['satellite_capacity_gbps'],
        'max_48_ghz_reproduction_error_gbps': error_48,
        'information': holding['information'], 'eligibility': holding['eligible_association'],
        'objective_tolerance_gbit': OBJECTIVE_TOLERANCE_GBIT, 'propagation': propagation,
    }
    (out/'config.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    for name, rows in [('capacity_edges', capacity_rows), ('capacity_summary', capacity_summary),
                       ('summary', summary), ('paired_effects', paired), ('periods', periods),
                       ('traces', traces)]:
        write_csv(out/f'{name}.csv', rows)
    write_report(out/'report.md', capacity_summary, paired, propagation, emission, gas_losses)
    print(f'Wrote {len(summary)} paired policy runs to {out}')


if __name__ == '__main__':
    main()
