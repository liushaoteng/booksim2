# 《Principles and Practices of Interconnection Networks》 核心摘要与代码指导
> 作者：William James Dally, Brian Towles
> 本文档基于全书理论精要提炼，专门为目前 BookSim 的小目标（无阻塞 Mesh、自定义拓扑映射与加速比测试）提供代码改造的理论依据和引注背景。

## 1. 拓扑结构设计 (Topology - 参考第 3 章)
**核心概念**：拓扑决定了网络的物理连接潜力，关键指标包括：
- **Network Diameter (网络直径)**：最远两点的跳数。
- **Bisection Bandwidth (对分带宽)**：切断网络恰好一半时需要切断的最小链路数乘积。
- **Mesh vs. Hypercube 的映射困境**：
  - Hypercube 具有优异的 $O(\log N)$ 理论直径和无可挑剔的路径多样性（Path Diversity），但高维模型在物理 2D 芯片上布线极其困难（长线延迟大）。
  - **代码指导**：我们的 `kncube.cpp` 改造正是基于降维打击思想。通过完美的图映射（例如格雷码编码转换），我们将高维逻辑上的“1-bit 差异连线”强行绑定在 2D Mesh 物理相邻的 Router 之间，从而在物理限制下复原理想的图特性。

## 2. 无阻塞网络理论 (Non-blocking Networks - 参考第 4 章)
**核心概念**：在任意输入端想要连接到任意未被占用的输出端时，网络内部的路由路径永远不会发生冲突。
- **严格无阻塞 (Strict-sense non-blocking)**：如 Crossbar 开关，无需重排（Rearrange）。
- **重排无阻塞 (Rearrangeably non-blocking)**：如 Benes 网络。
- **Mesh 下的工程逼近**：Mesh 本质上是阻塞网络（Blocking）。
  - **代码指导**：为了在 BookSim 中测试 “Non-blocking” 下的极限加速比，我们的关注点不应仅仅是算法，可能还需要**改变网络内部加速比参数 (Internal Speedup)** 并在 `TrafficManager` 中消除头端队列阻塞（Head-of-Line Blocking）。通过拉高 Router 内部 Crossbar 通道和增大 Virtual Channels 数量来屏蔽结构冲突，测试纯粹数学路由协议的极限效率。

## 3. 路由与死锁避免 (Routing & Deadlock - 参考第 8 / 14 章)
**核心概念**：死锁（Deadlock）的根本原因是**信道依赖图 (Channel Dependency Graph, CDG)** 中出现了极其隐蔽的闭环。
- **Dally 的死锁破除铁律**：只要给循环依赖图切断一刀（分配一个额外的虚拟通道或者禁止某种转向），即可防死锁。
- **Turn Model (转向模型)**：如 West-First, North-Last 路由，通过禁止某几个特定的拐弯动作来打破 XY 平面上的死锁环。
- **Escape VC (逃生虚通道)**：完全自适应路由（Fully Adaptive Routing, 如 Valiant）容易引起环路，必须预留一条采用确定性路由（如 DOR）的 Escape VC，作为死锁爆发时的兜底通道。
  - **代码指导**：在我们即将写入 `routefunc.cpp` 的自定义 Hypercube 路由代码中，如果纯粹按位匹配导致了非对称转向（比如允许由北向东又允许向西循环），必须要在代码里控制 `vcBegin` 到 `vcEnd` 的虚通道分配。如果是自适应匹配，务必预留至少 1 个 VC 强制使用 `dor_next_mesh` 兜底，防止在高注入率下仿真彻底 Hang 住。

## 4. 仿真统计方法论 (Simulation & Evaluation - 性能测评章)
**核心概念**：网络是一个典型的排队系统（Queueing System），符合 Little's Law ($N = \lambda \times T$)。
- **Latency 的组成**：
  - $T_{zero-load}$ (理论极小延迟)：包头大小 + 路由跳数 $\times$ 逐跳时延。
  - $T_{queueing}$ (排队延迟)：随流量注入率飙升呈现指数级爆炸的部分。
- **状态的划分阶段**：
  1. **Warm-up（热身）**：网络刚启动为空，此时的低延迟是假象，数据不能作为统计。
  2. **Steady-state（稳态）**：队列达到平衡，开始精准算分。
  - **代码指导**：这也正是我们在实施计划中强调“不要使用静态大进程”而要“引入 Python 动态并行”的理论根基。因为靠近饱和点（Saturation Point）时，BookSim 需要海量的周期去解析爆满的等待队列，导致仿真耗时不对称。我们要利用批量脚本去扫描临界点。
