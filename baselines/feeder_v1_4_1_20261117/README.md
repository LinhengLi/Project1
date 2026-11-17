# V1.4.1研究计算冻结快照

冻结日期：2026-11-17。快照保留工作区相对目录结构于workspace/，并附测试、环境和逐文件SHA256。

## 核验

从原项目根目录运行 `.venv-ems/Scripts/python.exe scripts/freeze_feeder_v1_4_1.py`。再次运行只核验快照，不重跑仿真、不覆盖文件。manifest.sha256校验manifest，manifest校验所有载荷文件。SHA256用于完整性审计，不是数字签名或文件系统防写保护。

## 内容与范围

包含backend/app Python源码、feeder测试、相关脚本、研究记录与用户截图、各feeder阶段已有输入和结果、原feeder_v1及扩展场景引用轨道、依赖声明及实际包版本。未打包虚拟环境、数据库、服务日志或整个网页系统；这是研究基准快照，不是完整应用部署镜像。没有执行扩大规模实验或网页建设。

## 再运行

使用兼容Python环境与environment.json记录的依赖，从workspace根运行保留的scripts入口。主脚本仍有固定相对输出路径，因此不要在冻结workspace内直接运行写结果的入口。先将workspace复制到新的派生工作目录，再复现或开发；原始快照与feeder_v1不得覆盖。

现有GSO入口：scripts/run_feeder_gso_epfd.py；其输入、配置及代码哈希已在冻结时核对。测试通过记录见validation.txt。

legacy_bridge_validation.json为此前单独执行的桥接核验记录，主GSO入口不自动生成该文件。

## 已知边界与后续

该模型适于动态快速计算算法对比，不是完整ITU合规审查。10秒采样值不代表槽内连续变化；固定研究假设和参考窗口保持显式。后续按“下一步实验步骤与新对话接续_V1_4_1冻结后_20261117.md”创建派生实验。
