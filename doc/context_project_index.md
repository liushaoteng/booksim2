# BookSim Project Context Index

这份索引文件是本项目文档的统一入口。新会话进入本仓库时，优先读取这里，再按需展开后续文档。

## 设计原则

- `doc/` 保存项目事实、背景、计划、约束、方法论。
- `skills/` 保存“什么时候读哪些文档、按什么流程做事”的执行规则。
- 项目知识以 `doc/` 为准，`skill` 只负责装载和流程，不应成为知识主存。
- 文档命名统一采用 `类别_主题.md`。

具体命名规则见：

- `doc/constraints_document_naming.md`

## 新会话默认加载顺序

1. `doc/context_project_index.md`
2. `doc/architecture_booksim_codebase.md`
3. `doc/plan_project_roadmap.md`
4. `doc/plan_current_tasks.md`

如果任务与饱和吞吐、非阻塞加速比、Racke 极限流量相关，再补充：

5. `doc/methodology_saturation_scan.md`
6. `~/.codex/skills/booksim-saturation-scan/SKILL.md`

## 文档分类

### 1. 项目背景 / 架构知识

- `doc/architecture_booksim_codebase.md`
  作用：解释 BookSim 核心模块、关键代码路径、调试入口。
  适用：任何需要理解代码结构、定位修改入口的任务。

### 2. 项目目标 / 研究计划

- `doc/plan_project_roadmap.md`
  作用：定义长期研究目标、阶段划分、仿真原则、工程方向。
  适用：任何需要判断“为什么做这件事”和“是否符合主线计划”的任务。

- `doc/plan_current_tasks.md`
  作用：记录当前阶段任务清单和完成进度。
  适用：任何需要确认当前优先级、补齐 TODO、更新阶段状态的任务。

### 3. 实验方法 / 仿真经验

- `doc/methodology_saturation_scan.md`
  作用：保存饱和点附近 downward scan 的实验规则、判定口径和当前项目经验。
  适用：吞吐上限、无阻塞加速比、worst-case permutation、Racke 容量验证。

- `doc/methodology_racke_dsl_repro.md`
  作用：保存同事复现 `RackeTree` / `DSL` 仿真的构建、配置、脚本入口与 smoke-run 命令。
  适用：需要从仓库根目录直接 build/run 当前 `3x3` Mesh 验证流程的任务。

- `~/.codex/skills/booksim-saturation-scan/SKILL.md`
  作用：把上述方法学规则作为工作流装载到具体会话中。

### 4. 一次性分析产物

- `tests/analysis/*.md`
- `tests/data/*.json`

这类文件用于保存具体实验输出和阶段性分析结果，但不应替代 `doc/` 中的长期背景文档。

## 后续推荐的管理边界

建议按下面四类管理，而不是把所有内容都塞进 skill：

- `doc/architecture_*.md`
  放项目结构、模块关系、设计背景。

- `doc/plan_*.md`
  放研究路线、任务计划、阶段目标。

- `doc/constraints_*.md`
  放实现约束、工程规范、禁止事项、接口约定。

- `doc/methodology_*.md`
  放仿真方法、测量口径、实验判定规则。

- `doc/reference_*.md`
  放外部资料摘录、书籍笔记、论文摘要。

对应地，skill 只保留两类：

- `project bootstrap skill`
  负责新会话先读哪些文档。

- `workflow skill`
  负责某类任务的操作流程，例如饱和点扫描、批量跑批、结果汇总。

## 结论

最干净的做法不是“把所有东西都整合进 doc”或者“都塞进 skill”，而是：

- `doc/` 做项目知识库和事实源
- `skill/` 做入口和工作流编排

这样既能保持架构整洁，又能保证新会话有稳定背景可依赖。
