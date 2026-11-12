# 网络侧 QoS 资料

- **ITU-T Y.1540** 定义 IP 性能的测量点、测量区段与分组事件，涵盖传输时延、时延变化、丢包、容量和可用性。**Y.1541** 给出 IP 网络性能类别及其目标。本项目使用 GS 入口至星上馈电接收端的聚合业务交付量，完整路径的 IP 指标需按相应测量点另建模型。 [Y.1540](https://www.itu.int/rec/T-REC-Y.1540/en) · [Y.1541](https://www.itu.int/rec/t-rec-y.1541/en)
- **3GPP TS 23.501 §5.7** 将保障流比特率、最大流比特率和平均窗口，与优先级、分组时延预算、分组错误率等 QoS 特征分开。项目借鉴保障速率与评价窗口配套的做法，采用独立定义的合成交付目标。 [TS 23.501](https://www.etsi.org/deliver/etsi_ts/123500_123599/123501/16.17.00_60/ts_123501v161700p.pdf)
- **3GPP TS 38.300 §16.14** 分开定义网关至 NTN 载荷的馈电链路和载荷至终端的服务链路。 [TS 38.300](https://www.etsi.org/deliver/etsi_ts/138300_138399/138300/17.00.00_60/ts_138300v170000p.pdf)
- **Kassing 等，Hypatia，IMC 2020** 将转发状态更新与分组事件仿真分开，并检验了更新粒度对路径变化统计的影响。**Liu 等，C-LRST，2024** 在连续仿真中分别测量两地面站 TCP 路径的 RTT、吞吐量和地星链路切换。项目分别配置链路步长、关联保持周期和业务评价窗口。 [Hypatia](https://bdebopam.github.io/papers/imc2020-hypatia.pdf) · [C-LRST](https://arxiv.org/html/2410.24039v1)
