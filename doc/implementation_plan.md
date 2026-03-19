# BookSim NoC 仿真研究与测试计划 (Simulation Methodology Plan)

## 1. 核心研究目标 (Core Objectives)
根据项目规划，整体研究分为“一小一大”两个阶段：

### 阶段 1：小目标（当前聚焦）
在原生的 **Wormhole + Virtual Channel (VC)** 交换架构下，研究 Mesh 拓展拓扑在 **non-blocking（无阻塞或极低竞争）** 条件下的加速比。包含：
- 测试无阻塞下不同路由算法的理论延迟下限。
- 横向评比经典路由与自定义路由算法在各个注入率下的饱和度表现。

### 阶段 2：大目标（远期开发）
突破原生架构限制，参考 **Nostrum NoC** 提出创新改进：
- 在 BookSim 源码中深度引入并实现 **Deflection Routing (偏折路由)**。
- 引入 **基于控制论的 Flow Control (流量级别控制)**。
- 加入 **QoS 优先级 (Quality of Service)** 特性保障不同权重流量。

## 2. 核心参考与文献 (References)
- **通用基础**：《Principles and Practices of Interconnection Networks》
- **偏折路由支持 (Deflection/Bufferless Routing)**：
  - 深入学习 Nostrum NoC 的无缓冲（Bufferless）或极简缓冲原理与选路策略。
  - **重点参考学者与文献**：重点研究 **Axel Jantsch**, **Zhonghai Lu**, 和 **Chaochao Feng** 等人在 Bufferless NoC 领域的核心学术论文（如流量行为建模、偏折选路、防活锁机制与优先级控制）。

## 3. 核心代码改造与算法创新引擎 (Core Code Modification & Innovation)
在小目标的网格无阻塞测试阶段中，加速比的研究需要对模拟器底层进行深度的外科手术：

### 3.1 拓扑图映射与节点重编号 (Topology Mapping & Node Re-indexing)
- 为了在物理 Mesh 网络上逼近无阻塞（Non-blocking）的极致加速比，必须将更高维的逻辑图（如 Hypercube，超立方体）映射嵌入到低维的 Mesh 节点中。
- **源码改造落地点**：必须打破 BookSim 默认的线性 `ID = y * k + x` 编号，深度修改 `src/networks/kncube.cpp` 中的 `_BuildNet` 以及邻居感知逻辑（`_LeftNode` 和 `_RightNode`），引入格雷码或其他自研的完美图映射坐标系算法。这也是**“小目标”代码最核心的改动发力点**。

### 3.2 自定义路由与灵感迭代 (Routing Algorithm Iteration)
除了对比经典算法（如 DOR 基础算法、ROMM/Valiant 高级算法），**创新的路由算法是小目标的核心竞争力**。
- **创新灵感与实验闭环**：这些前沿算法的构建将高度依赖**理论计算机科学论文 (TCS Papers)**（图论证明、界限推导）加上与 **AI Agent (如 Gemini)** 高频的结对编程与灵感探讨，从而实现理论从纸面数学公式到 BookSim C++ 路由引擎的极速转化。

### 3.3 推荐核心架构与技能链 (Recommended Architecture & Skills)
为了高效落地上述创新，推荐搭建完全解耦的**仿真-分析流水线架构**：
- **底层仿真微内核 (Engine)**：`C++11/14` (BookSim 源码剖析与扩展)，要求熟知 OOP 和 Router 流水线机制。
- **运筹与并发调度器 (Controller)**：`Python 3` + `multiprocessing/concurrent.futures` 动态任务调度队列，结合 Bash 脚本执行批量测试（横扫注入率与对比算法池）。
- **数据流洗牌与可视化库 (Analytics)**：`Pandas` 用于清洗数千次模拟产生的大量单独日志（如吞吐、抖动、跳数统计），利用 `Matplotlib/Seaborn` 自动化渲染具备“高学术完备性”的曲线对比全景图。

## 4. 科学仿真原则 (Scientific Simulation Methodology)
未来的任何对比参数修改，必须严格遵循：
- **热身周期 (Warmup)**：消除初始建立稳态的误差 ( `warmup_periods >= 3` )。
- **采样周期 (Sample)**：只抓取稳态下的包以获取极度精确的 Latency。
- **流量覆盖 (Traffic Coverage)**：不仅使用 `uniform`，必须补充 `tornado` 或 `bitcomp` 测试对抗极端流量的能力。

### 4.1 仿真测试并行化与任务调度优化 (Multi-Process & Parallel Optimization)
考虑到多路由算法、多拓扑大小、多条流量模式的组合参数空间（Parameter Space）巨大，必须采用**运筹优化级别的多进程并行机制**，极大幅度地缩短结果的壁钟时间（Wall-Clock Time）：
- **任务解耦与切片 (Task Slicing)**：依据路由算法（Routing Algorithm）和流量注入率集合（Injection Rates Set）的正交属性切分成大量细粒度原子任务（Atomic Jobs）。
- **动态负载均衡机制 (Dynamic Load Balancing vs. Static Partitioning)**：
  - 不做简单的静态死板分配（例如不单单按算法划分进程）。由于网络在高负载（高注入率、接近饱和点）情况下的计算复杂度远超空载状态，**静态分配极易导致某一个进程陷入“滞后拥塞阶段的长尾瓶颈”（Straggler Effect）**。
  - 核心要求：设立主从机制（Pool/Queue），工作节点 (Worker Processes) 异步消费测试配置队列。确保每个 CPU 核心全负荷运转，消除性能木桶上的短板。
  - **解耦输出与聚合**：每个子仿真进程独立输出带有配置哈希签名的单独 `.csv` 或 `.json`，仿真结束后由主进程统一通过 Pandas / Matplotlib 等合并绘制最终的 Latency-Throughput 对比性能曲线。

## 5. 分析指标 (Result Analytics)
- **Speedup Ratio (加速比提取)**：纵向对比相同框架下各种路由设计的峰值吞吐量。
- **Zero-load Latency (零负载延迟)**：判断控制流的理论最优时延。
