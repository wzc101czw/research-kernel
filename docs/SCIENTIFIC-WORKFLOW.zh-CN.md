# Scientific Research Kernel v0.3：科研对象与验证流程

> 本版本建立 **数据结构、状态转换和来源检查**；它不会自动证明一项科学结论正确，也不会自动验证人类身份。

## 一、和 v0.2 的关系

保持旧的 `workspace/tasks/`、`memory/`、`knowledge/claims/`、`assets/registry/` 不变。新增 `science/`，将 **为什么研究、怎样研究、观察到什么、如何推断和谁进行了审查** 与纯任务执行分离。

| 对象 | ID 前缀 | 对象关系 |
|---|---|---|
| Question | `rq-` | 研究问题 |
| Hypothesis | `hyp-` | `addresses` RQ / `competes_with` Hypothesis |
| Study | `study-` | `addresses` RQ；`mode` 区分研究类型 |
| Protocol | `protocol-` | `for_study` Study / `tests` Hypothesis / `amends` Protocol |
| Run | `run-` | `follows` *frozen* Protocol |
| Observation | `obs-` | `produced_by` Run |
| Analysis | `analysis-` | `uses_observation` Observation / `interprets` Hypothesis |
| Scientific Review | `review-` | `reviews` Protocol、Analysis、Hypothesis、Run 或旧 Claim |

## 二、一条确认性实证研究的最小路径

```bash
python rk.py science new question --title "Does context caching reduce agent failures?"
# 记下输出并替换 RQ_ID
python rk.py science new hypothesis --title "Context caching lowers failure rate" --link addresses RQ_ID
# 记下 HYP_ID
python rk.py science new study --title "Controlled agent comparison" --mode empirical --link addresses RQ_ID
# 记下 STUDY_ID
python rk.py science new protocol --title "Paired benchmark protocol" --phase confirmatory --link for_study STUDY_ID --link tests HYP_ID
# 记下 PROTOCOL_ID
```

对于确认性 Protocol，逐项录入 `design.variables`、`design.controls`、`design.outcomes`、`design.analysis_plan`、`design.stopping_rule`。例如：

```bash
python rk.py science set PROTOCOL_ID --key design.variables --value "context strategy" --reason "design"
python rk.py science set PROTOCOL_ID --key design.controls --value "same model, budget and tools" --reason "design"
python rk.py science set PROTOCOL_ID --key design.outcomes --value "task success, resource cost" --reason "design"
python rk.py science set PROTOCOL_ID --key design.analysis_plan --value "paired bootstrap intervals" --reason "design"
python rk.py science set PROTOCOL_ID --key design.stopping_rule --value "all preregistered tasks finished" --reason "design"
python rk.py science freeze PROTOCOL_ID --reviewed-by "Human Researcher"
```

`freeze` 后原记录不可修改。若方案需调整：

```bash
python rk.py science amend PROTOCOL_ID --reason "new confounder found"
```

返回的是新 Draft Protocol ID，旧 Frozen ID 保留。Run 必须显式引用冻结的 Protocol：

```bash
python rk.py science new run --title "Baseline run" --link follows PROTOCOL_ID
# RUN_ID
python rk.py science new observation --title "Observed outcomes" --link produced_by RUN_ID
# OBS_ID
python rk.py science new analysis --title "Paired interpretation" --link uses_observation OBS_ID
# ANALYSIS_ID
python rk.py science new review --title "Independent review" --link reviews ANALYSIS_ID
# REVIEW_ID
python rk.py science finalize REVIEW_ID --reviewer "Researcher" --decision inconclusive --reason "Need replication"
```

**注意：** 这里的新对象仅是科研记录，并不会因为创建 Run 就自动执行模型，也不会因为创建 Observation 就代表已获得测量。应当为相应对象增加真正的 `--source`（版本化小型 Manifest、日志摘要、实验输出）或已发布的 `--asset-ref`。

实际获得结果后，按顺序将具有真实来源的 Run、Observation 和 Analysis 固定为不可在 CLI 中直接编辑的 `sealed` 状态：

```bash
python rk.py science seal RUN_ID --recorded-by "Researcher"
python rk.py science seal OBS_ID --recorded-by "Researcher"
python rk.py science seal ANALYSIS_ID --recorded-by "Researcher"
```

封存前需要真实的 Source 或已发布 Asset 引用。Observation 的上游 Run 必须先封存，Analysis 引用的 Observation 也必须封存；对于理论研究，可用有来源的数学分析/证明记录，无需凭空创建实验。命令只冻结元数据记录，**不意味着真实验证通过**。

## 三、不同研究模式

`study --mode` 支持 `empirical`、`theoretical`、`systems`、`simulation`、`exploratory`。理论研究可以使用形式化 Proof 文件、Analysis 和 Review，不要求凭空创建 Dataset、Run 或 Observation。定性研究同样应当保留观察来源与分析依据。

## 四、历史成果迁移

旧资料可能已经有实验结果。你可以事后为它建立 Question/Study/Analysis 结构，但**必须注明 retrospective**，不能把事后整理的 Protocol 宣称为实验前预注册。历史结果是否有效，需要重新查看真实论文、代码和数据；树形目录本身不能证明任何科学结论。

## 五、设计边界

- 这是轻量科研对象登记工具，不是统计推断引擎、定理证明器或安全审批系统。
- `science finalize` 只登记 Review 的 Reviewer/Decision；不自动把原来的 Claim 升级为 verified。
- `science check` 与 `rk.py doctor` 检验 Schema、ID、部分关系、SHA 一致性和状态边界，不验证研究质量。
- 临时数据、未经许可的数据集和访问凭据不应写入 Context、Memory 或仓库。
- 内部表示兼容 W3C PROV 的实体/活动/参与者思想，日后可导出 RO-Crate；v0.3 尚未提供正式标准兼容性导出。

参考：https://www.w3.org/TR/prov-o/ ； https://www.researchobject.org/ro-crate/specification/1.3/
