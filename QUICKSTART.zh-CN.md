# Research Kernel v0.2 中文快速入门

本版本在 v0.1 的 Task、Handoff、Memory、Claim 和 Skills 上新增 **Research Asset Registry**。

## 初始化

```bash
python rk.py init
python rk.py doctor
python -m unittest discover -s tests -v
git init
git add .
git commit -m "Initialize Research Kernel"
```

## 新增：科研资产管理

如果不想逐项写 CLI 参数，直接运行 `python rk.py asset wizard`，按终端提示填写类型、标题、来源、许可、存储 URI 等。向导只创建 Draft，不下载任何数据，也不会自动发布。

```bash
# 创建 Raw Dataset 元数据（不下载数据）
python rk.py asset new dataset --slug research-corpus --version v1 \
  --title "Research Corpus" --owner "My Lab" --license "unknown" \
  --uri "store://lab/corpora/research-v1.tar.zst"

# 人类在自己的编辑器中修改元数据
python rk.py asset edit dataset:research-corpus@v1 \
  --reason "补齐来源、Hash 和数据协议" --editor "code --wait"

# 绑定本机 NAS / 硬盘路径，映射不会被提交到 Git
python rk.py store bind lab --path "/mnt/research-data"

# 完整数据已准备好时再校验，必要时审核发布
python rk.py asset verify dataset:research-corpus@v1
python rk.py asset publish dataset:research-corpus@v1 --reviewed-by "Researcher"

# 所有资产与结构检查
python rk.py asset list
python rk.py doctor
```

对于 `asset verify`，只有提供了真实 64 位十六进制 `storage.sha256` 并且本机存在对应文件时才会成功。这个值应由研究者对实际 Payload 计算，而不是让模型生成。

## 旧成果 / Benchmark / 论文与报告

- 旧成果：`research/archive/` + `legacy:slug@version`。
- 全局 Benchmark：`benchmarks/definitions/global/` + `benchmark:slug@version`。
- 大型 Dataset：Git 中只有 `assets/registry/dataset/` 的 JSON，原始数据在 NAS/S3/外置盘。
- 论文和给人读的报告：`research/publications/` + `paper:` 或 `report:` 版本记录。

具体命令示例、Metadata 字段和 DVC 接入见 [DATA-STORAGE.zh-CN.md](docs/DATA-STORAGE.zh-CN.md)。

## 原有研究工作流保持不变

```bash
python rk.py task new --title "Reproduce an Agent Benchmark" --next "Collect configs"
# 使用返回的 TASK_ID：
python rk.py task set TASK_ID --status active --next "Run baseline" --note "Original protocol located"
python rk.py handoff TASK_ID --note "Please replicate before accepting claims"
python rk.py context --task TASK_ID --max-chars 12000
```

创建研究 Claim 时，可额外指定发布过的 Dataset/Benchmark 引用：

```bash
python rk.py claim new --statement "Candidate result" \
  --source knowledge/evidence/notes.md \
  --asset-ref dataset:research-corpus@v1
```

`--source` 必须是真实存在、体量小且保存在当前 Git 工作区中的文件；`--asset-ref` 是科研资产的稳定、版本化引用。Claim 默认是 `provisional`，不会自动验证。

## v0.1 升级须知

在**备份并提交当前工作**之后，复制新版 `rk.py`、`rk_assets.py`、新增文档、`methods/skills/` 和测试到已有仓库。不要直接覆盖你修改过的 `AGENTS.md`、`workspace/policies.md` 等个人配置，应手工合并新增的资产索引规则。运行 `python rk.py init` 可以无破坏地补建缺少的目录/入口文件，旧 Task/Claim/Memory JSON 无需迁移。

如果你从未使用过旧版，直接解压新版项目即可。详细设计请看 `ARCHITECTURE.md`。
