# Research Kernel v0.4 — Typed Research Execution

> 版本目标：从科研对象存储升级为具有明确 Plan/Step/Execution 语义的最小科研执行系统。**这不是完整的自动科研 Agent 框架，也不构成容器级安全沙箱。**

## 1. 架构与边界

原有 `science/`、`assets/registry/`、`knowledge/`、`memory/`、`methods/skills/` 等目录和对象格式保持不变。

```
Study + Frozen Protocol
        | version-authority
        v
plans/specs/PLAN_ID.json       # Git 跟踪；声明式 Plan、有限内置操作、Typed DAG
        | python rk.py plan check
        v
plans/locks/PLAN_ID.json       # Git 跟踪；Human Review 标签 + Plan/Protocol/Policy/代码 Hash
        | preflight + context-closure
        v
.rk/executions/PLAN_ID/EXEC_ID/  # 本地状态；被 Git 忽略
        | plan export (显式、人工核对)
        v
experiments/runs/*.json        # 可由 Git 跟踪的小型计算 Manifest
        | source-ref
        v
Science Run -> Observation -> Analysis -> Scientific Review -> Claim
```

Plan **不是** Task：Task 表示一项要做的工作；Plan 描述执行 DAG 及各步可做的操作；Study 与 Protocol 定义其科学目的和方法学约束。Plan **不是**实验有效性证明；成功率差值仅是数学计算。

### v0.4 完成的范围

- 纯 Python 标准库、离线、本地优先，作为 v0.3.1 的增量升级。
- 类型化 Step，显式依赖、输入类型、Hash、输入输出契约；拒绝环形依赖和未列入白名单的操作。
- 只读 `plan check` 与 `plan dry-run`。后者还检查每个 Step 的必要上下文是否能装进预算。
- Review 后生成 Plan Lock；检测冻结后编辑、源码/Protocol、Study/Policy 和运行代码变化。**reviewed_by 只是自述标识，没有身份认证**。
- 单节点 Context Packet：包含 AGENTS、Policy、Study、Frozen Protocol、Plan Need/Spirit、当前 Step 和显式声明的依赖。内容是源对象的导航摘要，并不加载原始 Raw Dataset。
- 内置确定性操作：`sha256_file`、`validate_json`、`jsonl_rate`、`compare_rates`；不执行用户写入的 shell/python，不调用远端 API。
- 每个 Step 的输入摘要、上下文摘要、执行环境概览、输出摘要与本地恢复账本。
- 人工触发的 `plan run --max-steps N` 暂停、`plan resume` 恢复和显式 `plan export`。

### 关键限制

- **没有真正的进程/容器隔离**：内置操作在运行 `rk.py` 的可信 Python 进程中执行；Plan 声明的 `network: not_used` 意味着内置代码不调用网络，而不是 OS 强制禁网。不要让不可信 Agent 获得宿主 Shell 的任意权限。未来容器/集群执行后端需作为独立接口增加。
- **没有强身份认证和防恶意篡改**：Hash 与 Git 可以检查意外漂移，不能对抗有整个仓库写入权限的恶意用户。
- **不处理大型 Payload**：内置工作流仅接收位于仓库中、单文件不超过 32 MiB 的允许文件（不包含 `data/`、`.rk/`、`secrets/` 等）。大型数据仍采用 v0.2 的外部 Asset Registry；未来引入受控的数据挂载/存储代理。
- **不是任意程序的可靠性保证**：`jsonl_rate` 只接受 JSONL 中 bool 或整型 0/1 的指定字段，不推断样本独立性、评分可信度或缺失数据是否合理。
- 不创建/修改科学 Claim，也不根据运行成功自动生成通过审查的 Observation。

## 2. 快速体验（合成数据）

Python >= 3.10：

```bash
python rk.py init
python rk.py doctor
python -m unittest discover -s tests -v

python rk.py science new study --title "Synthetic benchmark study" --mode empirical
# 把输出记作 STUDY_ID
python rk.py science new protocol --title "Toy protocol" \
  --phase exploratory --link for_study STUDY_ID
# 把输出记作 PROTOCOL_ID
python rk.py science freeze PROTOCOL_ID --reviewed-by "Researcher"

python rk.py plan create --title "Toy benchmark comparison" \
  --study STUDY_ID --protocol PROTOCOL_ID \
  --left examples/fixtures/baseline.jsonl \
  --right examples/fixtures/candidate.jsonl --field success
# 输出 PLAN_ID
python rk.py plan check PLAN_ID
# 阅读并审查 plans/specs/PLAN_ID.json
python rk.py plan freeze PLAN_ID --reviewed-by "Researcher"
python rk.py plan dry-run PLAN_ID
python rk.py plan context PLAN_ID --step baseline \
  --manifest-out .rk/context/baseline.json
python rk.py plan run PLAN_ID --max-steps 1
# 记录返回的 EXEC_ID
python rk.py plan resume EXEC_ID
python rk.py plan status EXEC_ID
python rk.py plan export EXEC_ID --recorded-by "Researcher"
```

示例人工构造：Baseline 3/5 = 0.60，Candidate 4/5 = 0.80，差值约 0.20。**它不说明任何真实算法更优**，也没有进行统计显著性检验。

从执行中断恢复不需要长篇对话。新 Session 只要获得 `PLAN_ID` 和 `EXEC_ID`，便可通过 `plan status` 与局部 Context 恢复任务；运行的原始 JSON 记录在本机 `.rk`，跨机器只自动共享 Git 中经过导出的 Manifest。

## 3. Plan JSON 契约（精简说明）

`plans/specs/PLAN_ID.json`：

```json
{
  "schema_version": 1,
  "id": "plan-aaaaaaaaaaaa",
  "title": "Example",
  "need": "Compute success rates, without deciding scientific validity",
  "study": "study-aaaaaaaaaaaa",
  "protocol": "protocol-aaaaaaaaaaaa",
  "spirit": {
    "invariants": ["artifact_local_only", "frozen_protocol", "no_secret_content"],
    "review_required": ["scientific_interpretation_and_comparability"]
  },
  "environment": {
    "executor": "builtin-v1",
    "network": "not_used",
    "process_isolation": "none"
  },
  "steps": [
    {
      "id": "baseline",
      "op": "jsonl_rate",
      "depends_on": [],
      "inputs": {
        "data": {
          "type": "workspace_file",
          "path": "examples/fixtures/baseline.jsonl",
          "sha256": "actual SHA-256 must be filled here"
        }
      },
      "params": {"field": "success"},
      "context": {
        "required_refs": [],
        "required_skills": [],
        "max_chars": 16000
      }
    }
  ],
  "created_at": "2026-01-01T00:00:00+00:00"
}
```

这个代码块是**结构示意**，ID、Hash 和日期是占位值，不是可以直接运行的 Plan。可通过 `plan create` 生成可运行的真实记录，然后在冻结之前编辑 JSON 并重新执行 `plan check`。

内置操作 I/O：

| Operation | 输入 | 输出 | 说明 |
|---|---|---|---|
| `sha256_file` | `data`: workspace_file | `sha256`, `bytes`, `source` | 只读文件 Hash |
| `validate_json` | `data`: workspace_file | `valid`, `top_level`, `sha256` | 检查 JSON 可解析性，不泄露正文 |
| `jsonl_rate` | `data`: workspace_file | `trials`, `successes`, `success_rate`, `source_sha256` | 行为成功率；非统计推断 |
| `compare_rates` | `left/right`: step_output | `delta`, `baseline_rate`, `candidate_rate` | 只做算术差值，不验证 Run 比较条件 |

`compare_rates` 的 `depends_on` 必须包含且仅包含两条实际输入所引用的 `jsonl_rate` Step；Plan 按 DAG 拓扑顺序执行。

## 4. Context Engineering 的改变

不同于全局 Prompt 扩充，v0.4 的 `plan context` **从 Step 的已声明依赖出发**，仅输出局部决策所需的核心权威信息与引用。必要条件缺失或超出经审核的字符预算时，**直接拒绝**。

`context.required_refs` 可声明科学对象 ID、已发布科研 Asset 引用或已人工接受的 Memory ID。Memory 只能作为带有原始证据引用的指针，未审查或已失效的 Memory 会阻止该步骤；不会载入原始 Memory 来源正文。外部 Asset 只输出必要元数据（例如 ID、访问等级和声明的数据校验值），不会展示原始数据或私有存储路径。

`context.required_skills` 可声明 `methods/skills/NAME/SKILL.md` 中**确实存在的**操作方法；仅把本节点列出的 Skill 内容加载进局部 Context。其文件哈希也会进入 Plan Lock；执行期间修改 Skill 会使 Plan 失效。仓库本身对 Skill 作者没有身份认证，因此团队中仍需通过代码审查维护可信 Skills。

尚未实现：自动从所有科学关系递归推导完备依赖闭包、严格 Token 计数、带模型权限的 Context 分配、Context 压缩失真度评测。当前契约依赖研究者与 Agent 在计划设计阶段**显式列出必需依赖**。

## 5. 执行记录、恢复与科研发布

- **Preflight**：验证源文件 Hash、引用关系、Protocol 冻结状态、Context Authority（AGENTS/Policy/Study/Protocol/指定 Ref）和执行器实现版本。
- **Run**：每步保存 `.rk/executions/PLAN_ID/EXEC_ID/steps/STEP.json`，然后更新 `execution.json`。
- **Resume**：验证已完成结果的实际 SHA-256 与账本记录一致，重用完成节点，从待执行节点继续；如果输入/Plan/Protocol/权威上下文变化则拒绝，要求新版本。
- **Export**：只有完成的 Execution 可以手动导出到 `experiments/runs/*.json`；导出的是简短摘要和证据摘要，**不是原始日志、私钥、Prompt 或大型数据**。
- **Scientific Run**：研究者审查导出文件后，可执行 `science new run --link follows PROTOCOL_ID --source experiments/runs/...`，随后 `science seal`。这只是基于来源的记录，不代表研究假说得到证明。

注意：`plan status` 的运行信息只在产生它的那台机器可用；Git 不会同步 `.rk`。要跨机器迁移继续运行，需要另外的持久化执行存储/导入机制；当前最小版本仅保证本机恢复和 Git 层面的历史审计。

## 6. 与 v0.3.1 的兼容性

只需备份旧仓库、合并新的 `rk_execution.py`、`rk.py`、文档、Skills 和测试文件，再运行 `python rk.py init`。它只填充不存在的目录/模板，不覆盖现有 AGENTS/Study/Asset/Claim/Memory 文件。对存在的 `AGENTS.md`、README 和 Policy 应手工合并，不要直接强行覆盖。

建议在一个新的 Git 分支试升级：

```bash
git switch -c research-kernel-v0.4
python rk.py init
python rk.py doctor
python -m unittest discover -s tests -v
```

历史 Run/Claim/Memory 不会被自动迁移到 Plan。需要人类确认其科学含义后，再为未来实验创建 Plan。**禁止将历史实验 Protocol 事后伪装成预先冻结。**

## 7. 后续有证据价值的研究问题

1. 对真实 `flow_v41` 等 Benchmark 比较，结构化 Step + Context 是否减少跨 Session 语义漂移？
2. 不同 Step 粒度下的成功率、总 Token、模型调用次数、恢复开销和科学错误比例如何变化？
3. 如何实现真正的受限容器/队列执行器和外部 Dataset 的只读挂载，而不让 Agent 读取凭证？
4. 哪些 Integration Contract 可以静态验证，哪些需要专门统计分析与 Human Scientific Review？
5. 如何用标准化实验事实、反例和跨平台 Handoff 检查 Context Dependency Closure？
