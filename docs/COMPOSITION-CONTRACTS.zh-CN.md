# Research Kernel v0.3.1：组合契约与上下文必要条件

## 为什么添加这一层

各个 Run 独立通过结构/来源校验，不代表它们在科学意义上可直接合并。
我们借鉴数学中「局部与整体」的研究方向，但**没有**构造 Grothendieck
topos 或实现 Sheaf gluing 定理，也不声称程序可以判断科学结论是否正确。

## 现有接口

`python rk.py compose check RUN_A RUN_B --contract science/contracts/benchmark-comparison.v1.json`

预设 Contract 明确比较维度：数据版本、测试划分、指标定义、评分器版本和
计算预算必须相同；`context_strategy` 是允许变化、但必须有声明值的研究因素。
两项 Run 还必须引用同一个冻结的 Protocol。

**前提**：先通过 `science new run`、`science set RUN_ID --key design.FIELD --value ...`
记录维度，再附上真实证据并执行 `science seal RUN_ID`。

返回的三种状态分别是：

- `compatible_on_declared_dimensions`（退出码 0）：声明字段相容，但不表示科学结论成立；
- `incompatible`（退出码 2）：必需相等的字段或 Protocol 明确不一致；
- `insufficient_evidence`（退出码 3）：状态、来源、必要字段或 Protocol 不足以判定。

特别提醒：
- 修改 Contract 对应的是**改变比较的科学问题**，而不只是调整程序参数。
  应保留旧版本并审查新的规则。
- 真实的统计检验、混杂因素、污染和评分正确性不在此原型范围内。
- `same_protocol: false` 仍返回证据不足，因为跨 Protocol 的等价性需要独立审查。
- 在 `design` 填写值是研究者的声明，不等同于原始日志核验。

## 带必要 Protocol 的 Context

`python rk.py context --study STUDY_ID --protocol PROTOCOL_ID --profile audit --max-chars 14000 --manifest-out .rk/context/audit.json`

要求 Protocol 已冻结、确实关联 Study，并通过来源检查。Protocol 和 Study 都会作为
**必需上下文**；字符预算不足时拒绝生成该 Packet，而不是悄悄省略核心协议。

不显式给出 `--protocol` 时，Packet 标为 `navigation_only`，仍可用于浏览和探索，
但**不能被误当成具有完备前提的正式决策上下文**。

注意：这不是自动补全所有研究依赖的完整 Dependency Closure，当前仍需研究者
根据具体推断确定哪些 Protocol 与 Dataset/Metric 定义属于不可缺少的依赖。

## 下一阶段

1. 把完整的 Integration Contract 作为版本化、可审批的正式科学对象；
2. 用同一套接口语义约束 Plan 的输入、输出、可见作用域与副作用；
3. 让 Handoff/Memory 带上所属 Context、依赖版本和失效条件；
4. 使用真实的 `flow_v41` Benchmark 记录做反例测试与混杂因素审查。
