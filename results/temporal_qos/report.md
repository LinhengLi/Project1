# Continuous-window QoS experiment

See config.json for frozen link-only selection and metric definitions. Red shading: QoS selected link invalid.

|Scenario|Load/class|Reselect s|Policy|Eval s|High attainment %|Longest under s|Ordinary Gbit|Total Gbit|Mean Gbit/s|Switches|Invalid-under GS-s|
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
|decline_recovery|0.6|5|independent|30|55.92|30|158.00|576.00|4.800|15|0|
|decline_recovery|0.6|5|independent|60|31.73|30|158.00|576.00|4.800|15|0|
|decline_recovery|0.6|5|capacity_greedy|30|88.82|20|348.50|859.50|7.162|30|0|
|decline_recovery|0.6|5|capacity_greedy|60|77.88|20|348.50|859.50|7.162|30|0|
|decline_recovery|0.6|5|throughput|30|93.42|20|421.00|942.00|7.850|51|0|
|decline_recovery|0.6|5|throughput|60|88.46|20|421.00|942.00|7.850|51|0|
|decline_recovery|0.6|5|qos|30|93.42|20|421.00|942.00|7.850|57|0|
|decline_recovery|0.6|5|qos|60|88.46|20|421.00|942.00|7.850|57|0|
|decline_recovery|0.6|30|independent|30|53.29|30|135.00|502.50|4.188|10|50|
|decline_recovery|0.6|30|independent|60|41.35|30|135.00|502.50|4.188|10|50|
|decline_recovery|0.6|30|capacity_greedy|30|69.74|30|317.50|772.50|6.438|14|110|
|decline_recovery|0.6|30|capacity_greedy|60|59.62|30|317.50|772.50|6.438|14|110|
|decline_recovery|0.6|30|throughput|30|63.82|30|353.50|784.50|6.537|17|160|
|decline_recovery|0.6|30|throughput|60|43.27|30|353.50|784.50|6.537|17|160|
|decline_recovery|0.6|30|qos|30|63.82|30|365.00|810.00|6.750|17|135|
|decline_recovery|0.6|30|qos|60|39.42|30|365.00|810.00|6.750|17|135|
|decline_recovery|0.9|5|independent|30|63.16|55|199.12|627.36|5.228|15|0|
|decline_recovery|0.9|5|independent|60|49.04|55|199.12|627.36|5.228|15|0|
|decline_recovery|0.9|5|capacity_greedy|30|84.87|30|403.66|972.44|8.104|29|0|
|decline_recovery|0.9|5|capacity_greedy|60|87.50|30|403.66|972.44|8.104|29|0|
|decline_recovery|0.9|5|throughput|30|95.39|20|470.21|1065.18|8.876|40|0|
|decline_recovery|0.9|5|throughput|60|97.12|20|470.21|1065.18|8.876|40|0|
|decline_recovery|0.9|5|qos|30|96.05|20|482.87|1065.18|8.876|42|0|
|decline_recovery|0.9|5|qos|60|100.00|20|482.87|1065.18|8.876|42|0|
|decline_recovery|0.9|30|independent|30|57.24|55|171.09|548.47|4.571|10|50|
|decline_recovery|0.9|30|independent|60|50.96|55|171.09|548.47|4.571|10|50|
|decline_recovery|0.9|30|capacity_greedy|30|68.42|30|375.90|901.69|7.514|15|110|
|decline_recovery|0.9|30|capacity_greedy|60|57.69|30|375.90|901.69|7.514|15|110|
|decline_recovery|0.9|30|throughput|30|69.74|30|413.36|960.46|8.004|17|130|
|decline_recovery|0.9|30|throughput|60|52.88|30|413.36|960.46|8.004|17|130|
|decline_recovery|0.9|30|qos|30|59.21|30|489.64|960.46|8.004|17|130|
|decline_recovery|0.9|30|qos|60|38.46|30|489.64|960.46|8.004|17|130|
|stable|0.6|5|independent|30|100.00|0|202.50|697.50|5.812|11|0|
|stable|0.6|5|independent|60|100.00|0|202.50|697.50|5.812|11|0|
|stable|0.6|5|capacity_greedy|30|100.00|0|541.00|1107.00|9.225|18|0|
|stable|0.6|5|capacity_greedy|60|100.00|0|541.00|1107.00|9.225|18|0|
|stable|0.6|5|throughput|30|100.00|0|576.00|1152.00|9.600|106|0|
|stable|0.6|5|throughput|60|100.00|0|576.00|1152.00|9.600|106|0|
|stable|0.6|5|qos|30|100.00|0|576.00|1152.00|9.600|133|0|
|stable|0.6|5|qos|60|100.00|0|576.00|1152.00|9.600|133|0|
|stable|0.6|30|independent|30|100.00|0|147.00|639.00|5.325|11|0|
|stable|0.6|30|independent|60|100.00|0|147.00|639.00|5.325|11|0|
|stable|0.6|30|capacity_greedy|30|98.68|15|525.00|1080.00|9.000|14|15|
|stable|0.6|30|capacity_greedy|60|98.08|15|525.00|1080.00|9.000|14|15|
|stable|0.6|30|throughput|30|86.84|20|537.00|1074.00|8.950|19|65|
|stable|0.6|30|throughput|60|82.69|20|537.00|1074.00|8.950|19|65|
|stable|0.6|30|qos|30|82.89|20|531.00|1062.00|8.850|21|75|
|stable|0.6|30|qos|60|75.96|20|531.00|1062.00|8.850|21|75|
|stable|0.9|5|independent|30|100.00|0|237.00|742.50|6.188|11|0|
|stable|0.9|5|independent|60|100.00|0|237.00|742.50|6.188|11|0|
|stable|0.9|5|capacity_greedy|30|100.00|0|760.54|1350.35|11.253|19|0|
|stable|0.9|5|capacity_greedy|60|100.00|0|760.54|1350.35|11.253|19|0|
|stable|0.9|5|throughput|30|100.00|0|791.56|1431.46|11.929|91|0|
|stable|0.9|5|throughput|60|100.00|0|791.56|1431.46|11.929|91|0|
|stable|0.9|5|qos|30|100.00|0|863.69|1431.46|11.929|79|0|
|stable|0.9|5|qos|60|100.00|0|863.69|1431.46|11.929|79|0|
|stable|0.9|30|independent|30|100.00|0|174.00|675.00|5.625|11|0|
|stable|0.9|30|independent|60|100.00|0|174.00|675.00|5.625|11|0|
|stable|0.9|30|capacity_greedy|30|98.03|15|706.49|1315.72|10.964|15|15|
|stable|0.9|30|capacity_greedy|60|98.08|15|706.49|1315.72|10.964|15|15|
|stable|0.9|30|throughput|30|100.00|0|790.13|1428.65|11.905|10|0|
|stable|0.9|30|throughput|60|100.00|0|790.13|1428.65|11.905|10|0|
|stable|0.9|30|qos|30|100.00|0|862.82|1426.76|11.890|15|0|
|stable|0.9|30|qos|60|100.00|0|862.82|1426.76|11.890|15|0|

The 5s joint policies are the original freely reselected per-snapshot MILP reference, not a temporal look-ahead optimum. No queueing or end-to-end delay claim.

## Paired comparisons (percentage points; same frozen inputs)

- decline_recovery, load 0.6: QoS minus capacity-aware baseline: high attainment -5.92 pp; longest under-rate shortened by 0 s; ordinary delivery +47.50 Gbit; total delivery +37.50 Gbit. QoS 5s to 30s attainment loss +29.61 pp; longest under-rate 20 -> 30 s. Invalid selected links account for 135/165 under-rate GS-seconds (not necessarily the longest run).
- decline_recovery, load 0.9: QoS minus capacity-aware baseline: high attainment -9.21 pp; longest under-rate shortened by 0 s; ordinary delivery +113.74 Gbit; total delivery +58.77 Gbit. QoS 5s to 30s attainment loss +36.84 pp; longest under-rate 20 -> 30 s. Invalid selected links account for 130/160 under-rate GS-seconds (not necessarily the longest run).
- stable, load 0.6: QoS minus capacity-aware baseline: high attainment -15.79 pp; longest under-rate shortened by -5 s; ordinary delivery +6.00 Gbit; total delivery -18.00 Gbit. QoS 5s to 30s attainment loss +17.11 pp; longest under-rate 0 -> 20 s. Invalid selected links account for 75/75 under-rate GS-seconds (not necessarily the longest run).
- stable, load 0.9: QoS minus capacity-aware baseline: high attainment +1.97 pp; longest under-rate shortened by 15 s; ordinary delivery +156.33 Gbit; total delivery +111.04 Gbit. QoS 5s to 30s attainment loss +0.00 pp; longest under-rate 0 -> 0 s. Invalid selected links account for 0/0 under-rate GS-seconds (not necessarily the longest run).