# V1.5 本地预计算回放

在项目根目录运行：

```powershell
.venv-ems/Scripts/python.exe scripts/serve_feeder_openloop_v1_5.py
```

打开 http://127.0.0.1:8765/experiments/feeder_openloop_v1_5/ 。Ctrl+C停止服务。

页面仅读取results/feeder_openloop_v1_5中的预计算结果。无需启动旧态势系统，也不触发在线干扰重算。现代Chromium浏览器支持所需的DecompressionStream；不能直接双击HTML以file协议加载数据。

提供播放/暂停、帧跳转、速度、系统/网关/连线筛选，以及GSO口径、带宽、系统贡献和选站曲线切换。地图为活动卫星和站点经纬度示意；跨日界线连线省略。地图筛选不改变顶部全系统指标，EPFD贡献选择独立于地图系统筛选。

图中所有EPFD峰值限于已评价窗口，保护线只作为匹配配置的100%时间瞬时参考上限。单系统和合计分别关联Article22表22-1B及第76号决议表1B。

`?pilot=1`可加载3帧试跑数据，仅供开发检查；正式实验使用无查询参数地址。
