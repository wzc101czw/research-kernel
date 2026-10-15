# Legacy Workspace Intake：真实生产目录的只读迁移策略

上传样例是一份 `tree` 形式的目录路径清单，**不是实际研究文件内容或原始 Git 仓库**。本说明中的分类来源于路径/命名启发式，并不证明任何预测、评测或分析属于某次 Run。

## 使用方式

```bash
python rk.py intake tree /path/to/example.txt
# 生成本地 .rk/intake/latest/inventory.json 和 PLAN.md（被 Git 忽略）
python rk.py intake directory /path/to/actual/legacy/repo
# 同样只统计真实文件路径，不读取文件内容，不移动文件，不跟随 symlink 目录
```

可加 `--out-dir /safe/review/location` 将报告写入显式指定目录。报告中的文件名可能本身敏感，**默认本地 `.rk/`** 而不是提交 Git。

## 此次真实目录案例

来自提供的树形文本：1,604 个文件条目、41 个目录条目，包含 `.git/` 内部条目；其中 `data/` 下 1,142 个文件条目。**没有真实字节数、SHA、文件内容、Git tracked 状态或实验对应关系。**

| 原始路径模式 | 推测角色 | 推荐迁移方向 |
|---|---|---|
| `data/{swe_bench_pro,terminal_bench_2,travelplanner,vitabench,webarena_verified}/*.json` | Benchmark 数据或采样子集 | Dataset/Benchmark Asset 候选；原始 Payload 外置并保留小型 Manifest |
| `longrca-bench/data/*.parquet` | Raw Dataset | 不纳入普通 Git；只保存 Registry/Checksum/Storage Alias |
| `analysis/preds_*.jsonl`、`analysis/results_*.json` | 预测和评估输出 | 原始 Run Artifact；确认具体 Model/Harness/Protocol/Dataset 后建立结构化关系 |
| `analysis/compare*.py`、`solver/*.py`、`tests/*.py` | 可复用研究代码 | 留在 Git，补环境锁定/测试，稳定后提炼为 Skill 的确定性脚本 |
| `travelplanner/`、`swe_bench_pro/`、`terminal_bench_2/`、`vitabench/`、`webarena_verified/` 顶层 | 多 Benchmark 的 Agent Trace / 输出（推测） | 外部 Artifact Store；以 Run ID 连接数据与评测协议 |
| `docs/results_round*.md`、`docs/technical_report*.md` | 研究推理过程与面向人的报告 | Analysis/Report/Research Archive 候选，保留初稿与正式稿版本 |
| `memory/compact.md`、`memory/HANDOFF.md`、`memory/findings/*.md` | 历史上下文与研究摘要 | Handoff / Memory Candidate / Claim Candidate；全部需回源核实 |
| `memory/meta_methodology.md` | 过程方法论 | 审阅后归档到 `methods/meta/`，可提炼 Skill |
| `logs/*.log` | 执行日志 | Run Artifact，不直接写入长期 Memory |
| `.git/`、`solver/__pycache__/`、`_pdf_text*.txt` | Git 内部或可再生中间件 | 不当作正式科学发现、默认不加载进模型上下文 |
| `api_key.txt`、`.ipynb_checkpoints/api_key-checkpoint.txt` | 疑似凭证 | 安全审查；禁止直接入库/向 Agent 发送内容 |

## 安全优先顺序

1. 在原机器上核对疑似凭证是否真实有效以及是否进入过历史（例如 `git ls-files`、`git log --all --name-only`，只检查**路径**）；若确有泄漏，撤销/轮换凭证并按托管方建议清理历史。
2. 对原仓库做有权限控制的备份，保存当前 Git revision 与实际数据挂载位置。大文件是否已经进入 Git 历史，需独立验证。
3. 将每个主要研究课题登记为 Study Candidate，**不要根据文件名强制推断**哪份 `preds_` 对应哪份 `results_`。
4. 建立 Dataset/Benchmark Versioned Asset Manifest，核验外部 Payload 的大小、内容 Hash、授权与使用边界。
5. 再人工确认 Run / Observation / Analysis / Claim 的关系。对于历史课题，Protocol 必须标注 retrospective。
6. 数据迁移前后运行 `rk.py doctor`、实验复现测试，以及 Git 仓库内容/敏感文件检查。

## 不会做的事情

`intake` 工具不会自动创建 Science 对象、把数据拷进 Git、删除原件、修改文件名、读 API Key、解析日志语义，或凭目录名字宣布实验已被验证。

如果将来要实现受控迁移执行器，应当有明确的人工批准、持久化迁移日志、回滚计划以及内容 Hash 复核；v0.3 暂不包含该执行器。
