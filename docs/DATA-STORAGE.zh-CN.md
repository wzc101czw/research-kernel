# Research Kernel v0.2 — 科研资产与大数据管理

## 设计约束

1. **Git 只保存源码、元数据和小型可读文件**；大型 Raw Dataset、权重和完整实验输出留在 Git 之外。
2. **Asset Registry 不是 Dataset Downloader**：`rk.py asset new/list/edit/verify` 不会发起网络请求；`verify` 只读取用户已有的本地文件。
3. **Metadata 按版本冻结，允许有审计记录的编辑**：每个 `kind:slug@version` 是唯一身份。`draft` 可编辑；`published` 只允许 title、summary、tags、citation 等表述性修订。更换 Payload、协议、数据划分、许可证或扩大访问范围，应创建新版本；如发现数据泄漏风险，允许立即将 `access` 调得更严格并留下审计记录。
4. 通过 Git 管理 Manifest 的历史，并优先使用内容 SHA-256 和外部对象版本号；**声明 SHA-256 不等于校验通过**。
5. 许可证、访问权限和未脱敏科研资料应由有权限的人类研究者确认，不能交给 Agent 猜测。

## 目录层次

```text
assets/registry/{kind}/{slug}/{version}.json      # 所有资产的元数据 (Git)
benchmarks/definitions/global/                    # 实验室级正式 Protocol (Git)
benchmarks/definitions/project/                   # 项目实验性 Protocol (Git)
research/archive/                                 # 旧有成果说明、旧代码、历史笔记 (Git)
research/publications/                            # 给人读的论文 / 报告源文件 (Git)
knowledge/claims/                                 # 结论：仍以证据审查为准 (Git)
datasets/raw/                                     # 被 .gitignore 排除的大数据工作副本 (不进 Git)
.rk/stores.local.json                              # 本机存储挂载配置 (不进 Git)
```

**重要**：使用 `git check-ignore -v data/large.bin` 检查忽略是否生效。如果大型数据已经被提交到 Git 历史中，添加 `.gitignore` 无法清除历史中的大文件；需要专门的历史清理计划，先备份并协调协作者。

## 示例：登记一个外部 Raw Dataset

最容易上手的人工入口是 `python rk.py asset wizard`：交互式逐项录入 metadata，创建 Draft。复杂字段依旧可用编辑器完善。

首先登记 Draft（不需要下载或拥有数据本体）：

```bash
python rk.py asset new dataset \
  --slug my-corpus --version v1 \
  --title "实验语料第一版" \
  --owner "Research Lab" --license "research-only" --access restricted \
  --uri "store://lab/corpora/my-corpus-v1.tar.zst"
```

然后用以下命令编辑 JSON（`$EDITOR` 可以设为 VS Code）：

```bash
python rk.py asset edit dataset:my-corpus@v1 --reason "补充来源、Hash 和授权信息" --editor "code --wait"
```

在 JSON 的 `storage.sha256` 填入对**真实数据文件**计算得到的 SHA-256，`size_bytes` 填入字节数。

登记你的机器上的存储卷（配置只写到本地 `.rk/stores.local.json`）：

```bash
python rk.py store bind lab --path "/mnt/research-data"
python rk.py store list
python rk.py asset verify dataset:my-corpus@v1
```

该 `store://lab/corpora/my-corpus-v1.tar.zst` 将被解释为本机 `/mnt/research-data/corpora/my-corpus-v1.tar.zst`。其他 Agent 或机器可以把相同的 `lab` 别名绑定到**它自己的**位置，不必更改 Git 元数据。

如果数据在 S3/NAS，需要研究者自行按权限获取到本地后执行：

```bash
python rk.py asset verify dataset:my-corpus@v1 --file /path/to/downloaded-payload
```

以上步骤不会帮你下载数据。当 Dataset Manifest 有来源、权限、Checksum 等审核记录后，再由人类执行：

```bash
python rk.py asset publish dataset:my-corpus@v1 --reviewed-by "研究者"
python rk.py doctor
```

**审核提示**：`--reviewed-by` 是过程追踪字段，不是安全身份认证。技术上的审核需要仓库保护、代码审查或外部权限机制。

## 示例：一个真正可复现的全局 Benchmark

在 `benchmarks/definitions/global/my-benchmark/v1/PROTOCOL.md` 中定义任务、数据划分、指标、评分脚本的版本和复现要求。

```bash
python rk.py asset new benchmark \
  --slug my-benchmark --version v1 --scope global \
  --title "My Benchmark" --owner "Research Lab" --license "MIT" \
  --source benchmarks/definitions/global/my-benchmark/v1/PROTOCOL.md

python rk.py asset link benchmark:my-benchmark@v1 \
  --relation uses_dataset --to dataset:my-corpus@v1 \
  --reason "固定基准数据集版本"

python rk.py asset publish benchmark:my-benchmark@v1 --reviewed-by "研究者"
```

发布前应确保 Dataset 已发布。Benchmark 若需要更新 Metric、评分代码或 Dataset 划分，应保留 `v1` 的定义文件，并创建 `v2`。对于隐藏测试集，还必须把答案/评测标签隔离在 Agent 无法直接读取的权限域内，避免评价污染：

```bash
python rk.py asset fork benchmark:my-benchmark@v1 --version v2 --reason "修改指标与测试切分"
```

随后通过 `asset edit` 替换 v2 的 `sources` 和必要的 `relations`。禁止原地覆盖 v1 的 Protocol 文件；否则 `doctor` 会标记 STALE。

## 示例：导入旧成果、论文和研究报告

小型 Markdown/LaTeX 保存在 `research/archive/` 或 `research/publications/`；大 PDF、受版权限制的材料可只记录存储 URI：

```bash
python rk.py asset new legacy --slug old-agent-study --version v1 \
  --title "旧 Agent Benchmark 测试" --owner "Research Lab" \
  --license "unknown" --source research/archive/old-agent-study/notes.md

python rk.py asset new report --slug annual-review --version v1 \
  --title "年度研究报告" --owner "Research Lab" \
  --license "all-rights-reserved" --source research/publications/annual-review.md
```

论文可使用 `paper` 类型并在 `citation` 填写 DOI、完整引文，使用 `extra` 填写作者、会议、年份等。不要把旧笔记里的结论自动视为 Verified Claim。

## 人工修改元数据的两种方式

- **字段级 CLI**：`python rk.py asset set REF --field summary --value "修订说明" --reason "修正表述" --expected-revision 1`
- **GUI / JSON**：`python rk.py asset show REF > /tmp/edit.json` → 在 VS Code 中修改 → `python rk.py asset edit REF --from-json /tmp/edit.json --reason "人工补充信息"`

第二种方式保留了完整修改流程，可处理 tags、extra、relations 等复杂数据。编辑工具会验证 Schema、保持 ID 不变、追加 revision/history，并拒绝已发布版本的语义变更。不要直接改写 `assets/registry` 下的 JSON 跳过审计：`doctor` 主要验证形式与引用，**无法证明人工或外部工具没有手工绕过 history**。Git 提交记录能提供另一层人工审计。

## DVC 如何作为可选后端

本 Kernel **不依赖 DVC**，也不会自动执行 `dvc pull`。规模增长后，推荐使用 DVC 追踪 Raw Dataset 和模型权重，将 `.dvc` 指针加入 Git、把 Payload 放进 DVC Remote（NAS、SSH、S3、OSS 等）。Git Clone/Fetch 只操作其版本记录，需要另行明确运行 DVC 命令才能取得数据。

外部已有 Dataset 也可用 DVC `import-url --no-download` 记录来源而不下载；但如果来源会被覆盖，单靠 URL 无法重现历史版本，应使用 DVC Remote 保留副本、存储桶版本 ID 或不可变对象位置。

文档（官方）：
- DVC Remote Storage: https://doc.dvc.org/user-guide/data-management/remote-storage
- DVC Pull: https://doc.dvc.org/command-reference/pull
- DVC External Data: https://doc.dvc.org/user-guide/data-management/importing-external-data
- Git LFS behavior: https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs.adoc

## 现有版本的真实能力边界

- v0.2 支持对**单文件**计算 SHA-256。面对多 TB 分片数据，可以先把 `storage.uri` 指向冻结的 Manifest 文件，`storage.sha256` 代表 Manifest 自身；它**不能证明每个分片都完整**，需要额外校验所有分片或交给 DVC 实现。
- `doctor` 检查结构、依赖引用及 Git 内的小文件 Hash，不会读取远程 Payload，也无法证明 Benchmark 的科学有效性。
- `asset verify` 可能读取非常大的文件，请在有足够 I/O 预算时执行。
- 本地路径别名仅通过被 `.gitignore` 忽略的配置保存；不要把账户密码、Access Token、Signed URL 或患者/个人敏感信息放进 Git。
- 全局 Benchmark 目前指的是**本仓库**共享的 Definition；跨仓库共享还需选择一个权威 Benchmark 仓库，并对消费者锁定它的 Git Commit 或发布版本。
