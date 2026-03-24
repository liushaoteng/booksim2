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

### 3.1 基于外部配置文件的灵活拓扑图映射 (File-Based Topology Mapping)
- 为了在物理 Mesh 网络上逼近无阻塞（Non-blocking）的极致加速比，必须将更高维的逻辑图（如 Hypercube，超立方体）灵活地映射嵌入到低维的 Mesh 节点中。
- **核心工程设计原则（代码解耦与可扩展性）**：为了避免每次修改模型都要重新修改并编译 C++ 源码，采取**外部导入模式**替代 `kncube.cpp` 里的“硬编码污染 (Hardcoding)”：
  - **动态映射加载机制**：给 BookSim 的网络构建层（`kncube.cpp` 或通过 `Configuration` 传参）编写一套“映射解析器”。从外部自定义的 `.txt` / `.map` 甚至纯粹从参数配置里直接读取数组，并在初始化期间重新生成一套内部的 `Physical -> Logical ID` 和 `Logical -> Physical ID` 的映射查阅表（Lookup Table）。
  - **优势**：这一修改极其有利于后续实验的横跨验证！你可以通过 Python 脚本自由地随机生成或者穷举千万种打乱编号的拓扑矩阵映射图，直接通过命令行参数批量“喂”给同一个无需重新编译的 BookSim 核心引擎。这也是全工程**“小目标阶段最优雅的发力点”**。

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

## 5. 分析指标与微观测量体系 (Result Analytics & Micro-Metrics)
除了基础的宏观性能以外，需要对仿真分析进行深度增强：
- **Speedup Ratio (加速比提取)**：纵向对比相同框架下各种路由设计的峰值吞吐量。
- **Zero-load Latency (零负载延迟)**：判断控制流的理论最优时延。
- **包时延全景分布 (Latency Distributions)**：不仅关注均值 (Avg)，还必须解析输出最大值 (Max)、最小值 (Min) 以及 percentile 分位数（如 95th，99th 长尾延迟）。
- **配置与仿真语境自动记录**：所有生成的综合测试结果（JSON/CSV）必须自动带上当前测试括扑大小、注入率、包大小 (flits) 等关键配置元数据。

### 5.1 基于采样定律的队列拥塞监控 (Queue Length Sampling)
为了精准找出网络瓶颈而不被全量遍历拖垮系统性能，我们采取物理学上的**周期性采样 (Periodic Sampling)**：
- 在 BookSim 源码中引入采样间隔宏控制，比如 `queue_sample_period_cycles`（例如只在每隔 500 个仿真钟周期进行一次切片采样）。
- 在达到稳态 (Steady-state) 后，系统将周期性抓取所有基站节点内部所有队列（如 VC 队列）的待消费长度，最后统合输出队列长度的极大值 (Max) 与极小值 (Min)。

## 6. 工程测试目录体系架构 (Test Directory Reorganization)
- 严禁测试脚本与核心 C++ 源码混杂。要求所有的 Python 驱动框架（例如生成拓扑 `map_*.txt`，并发批量遍历路由，清洗生成图表等）全部挪入并归档在统一的独立 `tests/` 文件夹中。
- `src/` 目录严格保留纯净的跨平台编译底座，彻底分离数据控制流与模拟计算流。
