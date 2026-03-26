# 核心目标进度列表 (Project Tasks)

## 阶段 1：小目标 (当前聚焦：Wormhole & Routing 比对)
- [x] 制定并确认小目标的横评测试计划
- [/] 配置并验证 non-blocking Mesh 仿真环境配置
- [ ] 重构工程架构，将 python 测试与运行脚本统一整理至单独的 `tests/` 文件夹
- [ ] 修改 BookSim 源码以支持基于周期的队列长度采样统计（输出VC队列最大/最小长度），避免拖慢仿真器性能
- [ ] 丰富 Python 测试脚本体系，自动生成包含详细配置（包大小等）与精准时延（含最大/最小/平均/Percentile）的综合测试结果报告
- [ ] 批量跑批并对比基础路由算法与自定义算法
- [ ] 处理并提取网络加速比 (Speedup) 统计数据

## 阶段 2：大目标 (未来开发：Deflection Routing)
- [ ] 研究 Nostrum NoC，在 BookSim 设计 Deflection Routing 数据流
- [ ] 实现基于控制论 (Cybernetics) 的 Flow Control
- [ ] 实现并验证 QoS 优先级支持
- [ ] 对大目标架构进行大规模综合性能测试
