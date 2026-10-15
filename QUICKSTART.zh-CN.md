# Research Kernel v0.1：中文上手指南

本项目是一个可以直接运行的 Research Kernel 原型，**不是**完整的 Agent Framework。它不调用任何商业 LLM API，也不需要向量数据库；所有核心记录都是普通文件，可以提交 Git。

## 1. 安装与初始化

准备 Python 3.10+ 和 Git。解压后进入 `research-kernel-starter` 目录：

```bash
python rk.py init
python rk.py doctor
python -m unittest discover -s tests -v
git init
git add .
git commit -m "Initialize Research Kernel"
```

无需先安装第三方 Python 依赖。若计划用 uv 管理研究实验项目，可以随后使用 `uv sync` 生成并提交 `uv.lock`。第一次 Git 提交可能需要配置 `user.name` 和 `user.email`。

## 2. 用第一个真实研究任务跑通闭环

创建任务：

```bash
python rk.py task new --title "复查 Agent Benchmark 的结果" --next "整理原始实验设置"
```

记下返回的 `task-...`，后续用实际 ID 替换 `TASK_ID`。

将原始实验配置、论文笔记或小型日志放在 `knowledge/evidence/`（敏感、大文件请勿放入普通 Git），创建结论：

```bash
python rk.py claim new --statement "在条件 X 下方法 A 可能优于 B" --source knowledge/evidence/YOUR_FILE.txt --scope "数据集 X / 环境 Y" --assumptions "基线一致、随机种子已记录"
```

重要：创建的 Claim **始终为 provisional**，不会自动成为 verified。

记录阶段进度，交接给下一个 Agent：

```bash
python rk.py task set TASK_ID --status active --next "独立复现实验" --note "已定位关键实验配置"
python rk.py handoff TASK_ID --note "不要直接相信旧结论；请复核原始日志"
python rk.py context --task TASK_ID --max-chars 12000
```

Context 输出是字符数量限制，**不是精确 Token 预算**，也不会自动注入任何尚未挂载这个仓库的平台。

## 3. 使用 Memory

让 LLM 阅读适当的任务/交接/证据文件，遵循 `methods/skills/compact-memory/SKILL.md`，提出候选长期记忆：

```bash
python rk.py memory propose --kind failure --summary "旧测试未锁定环境，无法直接比较" --source knowledge/evidence/YOUR_FILE.txt
```

返回 `memory-...` 后，在终端执行：

```bash
python rk.py memory accept MEMORY_ID
```

终端提示要求输入 `ACCEPT`。该交互不是身份认证；若要真正限制 Agent 权限，需使用 OS 文件权限、单独审批服务或只读挂载。

## 4. 重新怀疑旧结论

```bash
python rk.py claim challenge CLAIM_ID --reason "新实验显示基线配置发生变化"
python rk.py doctor
```

`doctor` 检查来源 Hash；**若来源已更改，提示 STALE**。要么恢复原来源快照，要么依据新来源重新建立 Claim 并保留历史；不要为了消除报错而盲目刷新 Hash。

## 5. 跨平台使用

- Codex / Cursor：阅读根目录 `AGENTS.md`。
- Claude Code：阅读 `CLAUDE.md` 中的公共规则入口。
- Gemini CLI：通过 `GEMINI.md` 导入 `AGENTS.md`。
- API 或纯网页 Agent：需要你手动传入 `context` 生成内容，或让它通过获授权的工具访问项目文件。

前提是相关 Agent 真的有权访问当前仓库。Git 管理数据，并不自动赋予网页聊天系统读取本地文件的能力。

## 6. 当前系统的设计边界

- 文档级知识地图存在于 `knowledge/INDEX.md`；暂无语义向量索引。
- Memory Compaction 由 LLM 根据 Skill **提出候选**，CLI 负责保存与验证来源；尚未做自动周期调度。
- Skill 工厂是受控流程模板；`doctor` 只做简化的 Skill 元数据检查，不等于完整的 Agent Skills 规范验证或效果评测。
- 实验仍使用手工 Run Manifest；暂无自动版本锁定或 Benchmark 评测系统。
- `doctor` 不会证明论文结论是科学真理，只检查部分形式和来源一致性。

## 7. 推荐的下一个增量

在使用一个真实科研任务完成 Task → Evidence → Claim → Handoff → Memory → Challenge → Doctor 后，再增加：

1. `Experiment Manifest` 的 JSON Schema 与验证；
2. `SQLite FTS5` 检索和按文件 Hash 更新的派生索引；
3. Skill Regression Tests；
4. 视需要接入 MCP 和 Agent Runtime。

详细文件说明见 `ARCHITECTURE.md`，英文操作说明见 `README.md`。
