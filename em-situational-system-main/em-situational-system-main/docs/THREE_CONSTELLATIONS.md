# 本地三系统轨道导入

场景：`data/scenarios/three_constellations.json`。

轨道文件从工作区 `realdatas` 复制，保留原文件。Starlink TLE 共 10,611 条，OneWeb OMM 共 651 条，GEO OMM 共 568 条，总计 11,830 条。Starlink 尚未逐星划分授权代际，GEO 目录不等于已确认的 GSO 受保护通信系统。

新增 `mixed_local` 场景支持多个 TLE / OMM 文件，卫星 ID 添加星座前缀。OMM 直接传给 Skyfield / SGP4，不转换为五位编号 TLE。

初始仿真时刻：2026-11-13 12:00:00 UTC。数据历元并不完全一致，GEO 最早记录为 2026-10-15；这是快照传播演示，不是实时精密定轨。场景 `orbit_only=true`，仅显示轨道，不生成假定业务链路或执行平方级星间链路遍历。

在工作区 PowerShell 运行 `./scripts/start_ems.ps1`，访问 http://127.0.0.1:8000/static/constellations.html 。原页面为 `/static/index.html`，已添加三系统页面入口。

重新复制轨道文件：`python scripts/import_ems_constellations.py`。

验证导入和传播：`.venv-ems/Scripts/python scripts/verify_ems_import.py`。

三维页面支持分组开关、卫星详情、60 秒步进和重置。Cesium 与地图瓦片需要网络。启动依赖使用工作区 `.venv-ems`，复用现有 Anaconda 数值库；当前未安装可选 PyTorch，MAE 模块不属于此次轨道展示。
