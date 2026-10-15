# Integration Contracts

Contracts are **reviewable comparison specifications**, not evidence and not executable code.

`benchmark-comparison.v1.json` is a deliberately strict example. Modify the required
dimensions for the **actual research question** in a new versioned contract instead of
silently editing the comparison after looking at the results.

Run: `python rk.py compose check RUN_A RUN_B --contract science/contracts/benchmark-comparison.v1.json`

Three states: `compatible_on_declared_dimensions`, `incompatible`,
`insufficient_evidence`. A compatible result means only that the declared fields match.
Neither good scientific design nor a causal finding is established. The tool does not
read raw datasets, merge results, or write scientific claims.

Source-of-truth scientific records remain under `science/`. Every comparison must
record which contract version was used; this proof-of-concept prints that path.
