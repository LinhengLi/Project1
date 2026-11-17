# 验收测试报告

运行命令：

```bash
cd backend
python -m scripts.acceptance_tests
python -m pytest tests/ -v
```

## 结果摘要（14/14 通过）

| 验收项 | 状态 |
|--------|------|
| 星座/链路动态更新 | PASS |
| 频谱冲突判定 | PASS |
| 干扰样式覆盖（≥4种） | PASS（5种） |
| 态势生成 | PASS |
| 稀疏补全 25%/50% | PASS |
| 动态预测 30s/1min/5min/10min | PASS |
| 5维风险评估 | PASS |
| 下游接口载荷 | PASS |
| 态势更新延迟 <5s | PASS（~0.01s） |
| 补全对照实验 | PASS（IDW 相对 Kriging 提升 ~22%） |

## 演示场景

- 50 星 Walker 星座 @ 550km
- 3 地面站（北京/上海/西安）
- 5 类干扰源（同频/扫频/欺骗/宽带/自然）

## 已知限制（Phase 2）

- 千星规模压测未在本期验证
- GenSpectraLM / 3D Swin Transformer 完整复现待 Phase 2
- 半实物 SDR 验证待硬件到位后接入
