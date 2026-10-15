# v0.2 → v0.3 升级指南

1. 先在你自己的工作环境中备份并提交现有 v0.2 Git 仓库。不要直接解压覆盖已经编辑过的 `AGENTS.md`、`workspace/policies.md` 或已有记录。
2. 复制新版本 `rk.py`、`rk_science.py`、`rk_context.py`、`rk_intake.py`（以及与打包版本匹配的 `rk_assets.py`）；保留原来的 `assets/registry/`、`workspace/tasks/`、`memory/`、`knowledge/claims/` 和未提交的原始数据。
3. 合并 `AGENTS.md`、`science/INDEX.md`、`methods/skills/` 和 Policies 的新章节，让已有本地规则继续生效。不要用模板覆盖研究者修订过的约束。
4. 在仓库根目录运行：

```bash
python rk.py init
python rk.py doctor
python -m unittest discover -s tests -v
```

5. 从一个真实且已知来源的 Study 开始逐步登记；旧结果请明确标记 retrospective。不要先改动旧文件路径。
6. 对外部数据注册稳定 Dataset/Benchmark Asset 版本。`data/`、`.rk/`、缓存等仍排除在 Git 之外。
7. 以 `intake` 只读报告制作迁移任务清单，人工逐批确认，不允许 Agent 无审核批量搬运或删除旧文件。

**兼容性**：旧 Task、Claim、Memory、Asset JSON 的文件结构未被改写；默认 `context --task` 沿用旧输出。新 `doctor` 还会要求 `science/` 目录和 `science/INDEX.md` 存在，因此完成模块复制后要运行一次 `rk.py init`。
