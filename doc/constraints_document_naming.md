# Document Naming Convention

这份文档规定本项目 `doc/` 目录中的统一命名规则。

## 规则

所有 Markdown 文档统一使用：

`类别_主题.md`

要求：

- 全部使用小写字母
- 单词之间使用下划线 `_`
- 文件名只描述“归属类别”和“主题”，不夹杂临时状态词
- 长期背景文档放在 `doc/`
- 一次性实验结果放在 `tests/analysis/` 或 `tests/data/`

## 类别前缀

- `context_`
  项目入口索引和上下文导航文档。

- `architecture_`
  工程结构、模块关系、代码架构说明。

- `plan_`
  项目路线、任务列表、阶段目标、里程碑。

- `constraints_`
  工程规范、实现约束、命名规则、接口约定。

- `methodology_`
  仿真方法、统计口径、实验判定规则。

- `reference_`
  外部书籍、论文、资料的摘要或摘录。

## 当前映射

- `doc/context_project_index.md`
- `doc/architecture_booksim_codebase.md`
- `doc/plan_project_roadmap.md`
- `doc/plan_current_tasks.md`
- `doc/constraints_document_naming.md`
- `doc/methodology_saturation_scan.md`
- `doc/reference_dally_book_summary.md`

## 例外

- `manual.tex`
  属于 LaTeX 源文件，不强制改成上述 Markdown 命名模式。

- PDF 原始资料
  保留原书名或原始文件名即可，不强制改前缀。
