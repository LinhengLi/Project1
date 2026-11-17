# GSO参考接收站：一星一站一链路

当前方案：12颗GSO候选、12个不同位置的仿真接收站、12条固定关联。每颗卫星仅对应一个站，每站仅指向一颗卫星，不做换星。替代此前8点/18点方案。

## 对应关系

|卫星|接收参考位置|纬度|经度|24h采样最低仰角|
|---|---|---:|---:|---:|
|INMARSAT 5-F3|OW-FCC-001|62.333075|-150.0312306|15.208°|
|SES-17|SL-FCC-003|34.6023889|-117.4545556|23.696°|
|VIASAT-1|SL-C-017|22.8905|-109.9167|62.526°|
|ECHOSTAR 17|SL-C-059|19.65|-100.05|65.544°|
|INMARSAT 5-F2|SL-C-165|-3.119|-60.0217|83.019°|
|THOR 7|SL-C-159|6.4698|3.6015|80.878°|
|ECHOSTAR 19|SL-C-205|14.9032|-92.2577|71.572°|
|SES-15|SL-C-149|19.72|-155.08|52.558°|
|VIASAT-2|SL-C-216|12.1696|-68.99|75.609°|
|TELSTAR 19V|SL-C-071|13.062759|-59.537583|74.082°|
|ARCTURUS|SL-C-156|-3.977445|122.511309|81.017°|
|JUPITER 3 (ECHOSTAR 24)|SL-C-212|17.9893|-92.9472|68.694°|

保留SES-17/Adelanto与Inmarsat-5 F3/Talkeetna各一个初始参考点；其他卫星在现有NGSO目录站点中按初始仰角优先并排除已用坐标选取。位置用于简化几何实验，尚未核实实际波束覆盖，不宣称实际GSO网关或最优保护部署。原始锚点来源保存在配置文件中。

在2026-11-13 12:00 UTC起24小时内逐小时检查，所有链路仰角均>=10°，不保证采样间连续最小值。关联固定，SGP4位置继续随时间更新。

口径3.5m、效率0.65、18.2GHz、398K、最低仰角10°、海拔0m为实验假设。各卫星实际频段交集见GSO频段筛选文件；不能默认每颗都覆盖17.8–18.6GHz全部带宽。方向图、信道、波束和EPFD限值待配置，未启用实际干扰计算。12条关联是参考链路定义与可视化，不代表完整链路预算已实现。

动态优化对象为NGSO资源，GSO固定接收关联作为保护约束。独立对应不意味着物理上不存在跨链路干扰。

## 依据

- ITU EPFD说明：https://www.itu.int/epfdsupport/questions/
- ESA固定GEO链路说明：https://www.esa.int/Applications/Telecommunications_Integrated_Applications/Orbits
- 频段来源：https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/licences-and-certificates/list-foreign-satellites-approved-provide-fixed-satellite-services-fss-canada

配置：realdatas/GSO_reference_receivers.json；生成：scripts/configure_gso_receivers.py；同步：scripts/import_ems_constellations.py。