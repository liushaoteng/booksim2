# BookSim 代码架构分析与导读 (BookSim Architecture Analysis)

这份文档是对 BookSim 2.0 模拟器核心代码逻辑的系统性分析。在后续的对话与开发中，可以随时以本文档作为代码结构的背景上下文 (Context)。

## 1. 核心架构与模块全景 (Core Architecture Overview)
BookSim 是一个 Cycle-accurate（周期精确的）NoC 模拟器。代码呈现高度的模块化和面向对象设计，各组件严格解耦：
- **`main.cpp`**：模拟器入口点，负责加载配置（Configuration）并启动 `TrafficManager`。
- **配置系统 (Configuration)**：参数解析系统 (`config_utils.cpp`, `booksim_config.cpp`)，读取如 `meshconfig` 这类的纯文本文件并将配置送入内存变量。

## 2. 通信节点流：流量管理器 (TrafficManager.cpp)
**`TrafficManager` 是整个仿真的“心脏”。**
- **作用**：负责**包的生成 (Packet Generation)**、**注入阶段 (Injection)** 以及**退出阶段 (Ejection)**。
- **关键函数**：
  - `_Step()`：每个时钟周期的心跳引擎，驱动网络里所有的模块推演一个周期。
  - `_GeneratePacket()`：根据 `traffic` 类型（如 `uniform`、`tornado`）和 `injection_rate` 生成新包，并加入源节点的注入队列。
  - `_RetirePacket()`：当数据包到达终点被 ejection 出来时被调用，负责采样该 Packet 的生命周期、更新 Latency（延迟）统计信息。

## 3. 物理系统层：拓扑与网络 (Network / KNCube)
这部分代码构建了节点之间的物理“铜线”和网络结构图形。
- **`src/networks/network.cpp`**：网络基类，负责存储所有 `Router` 和 `Channel` 对象的指针数组。
- **`src/networks/kncube.cpp`**：K-ary N-cube (包含 Mesh 和 Torus) 拓扑结构的具体实现。
  - **核心职能**：通过 `_BuildNet()` 函数，数学化推理节点 ID（如根据 `node % gK` 计算 X, Y 坐标）并将其连线 (`AddInputChannel` / `AddOutputChannel`) 到对应的邻居。当你需要重定义 ID 或连线关系时，必然修改此处。

## 4. 路由逻辑层：路由器与路由算法
### 4.1 路由器模型 (IQRouter.cpp)
BookSim 中的默认和最主流的路由器是 **Input-Queued Router (IQRouter)**。
它的一个时钟周期内部经过标准流水线 (Pipeline)：
1. **RC (Routing Computation)**：读取 Head Flit（头微片），调用你写的路由函数，计算候选输出端口 (Output Port)。
2. **VA (Virtual Channel Allocation)**：通过各种 Allocator (如 iSLIP) 获取目标端口的虚通道所有权。
3. **SA (Switch Allocation)**：不同 Input 争夺内部 Crossbar 交叉开关的连通带宽。
4. **ST (Switch Traversal)**：Flit 正式穿过路由器。
5. **LT (Link Traversal)**：Flit 进入连向下一个 router 的连线 Channel。

### 4.2 路由算法挂载 (RouteFunc.cpp)
- **作用**：纯粹的逻辑计算集合。不涉及物理状态的存储。
- **函数签名**：`void my_routing(const Router *r, const Flit *f, int in_channel, OutputSet *outputs, bool inject)`
- **`OutputSet`**：通过 `AddRange(port, vc_begin, vc_end)` 将合法的方向和允许的虚拟通道返回给路由器的 Pipeline 进行下一步抢占。所有的拓扑路由算法必须在 `InitializeRoutingMap` 函数中被注册方能生效。

## 5. 调试与观察手段 (Watch & Trace)
- **`watch` 机制**：BookSim 可以在配置文件里跟踪特定的包（e.g., `watch_flit = 8;`）。`gWatchOut` 在源码中到处可见，当启用 watch 时，系统会把该包经历所有 Router、Buffer 的极高精度的 timeline 事件打印出来，这是排查死锁 (Deadlock) 和路由错误 (Route Logic Error) 时最有用的手段。

---
> 当你需要做二次开发时：
> - **修改流量模式** -> 看 `traffic.cpp` 和 `TrafficManager.cpp`
> - **修改拓扑连接规律** -> 看 `networks/` 下的文件
> - **修改路由算法 (方向决策)** -> 看 `routefunc.cpp`
> - **修改微架构 (如何调度VC和Crossbar)** -> 看 `iq_router.cpp` 和 `allocators/`
