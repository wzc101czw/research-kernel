---
name: benchmark-governance
description: Register global or project benchmarks with frozen protocols, dataset version references, scoring definitions and review gates. Use when creating, updating or running a reusable evaluation benchmark.
---
# Benchmark governance

1. Define the exact task, scoring script, metric direction, aggregation, split policy, known leakage risks, baselines and allowable resources under `benchmarks/definitions/`.
2. Keep definition files small and Git-tracked. Isolate hidden test labels from the solving Agent; enforce evaluator/tool permissions so Benchmark data does not leak into the research context. If there are large inputs or hidden test sets, register them as `dataset:SLUG@VERSION` first; do not put them into Git.
3. Create a draft benchmark record: `python rk.py asset new benchmark --slug SLUG --version v1 --title TITLE --owner OWNER --license LICENSE --scope global --source benchmarks/definitions/PROTOCOL.md`.
4. Link the exact dataset: `python rk.py asset link benchmark:SLUG@v1 --relation uses_dataset --to dataset:DATASET@v1 --reason 'pin evaluation corpus'`.
5. Run benchmark smoke tests and validate the metric implementation. Human reviewer publishes via `asset publish --reviewed-by ...`; record experiment manifests with Git commit, benchmark ref and evaluation implementation hash.
6. Never change dataset, metric or split definitions in-place after publishing. Fork to a new version and document expected impact on comparability.
7. Use `python rk.py doctor` to detect stale protocol files and invalid asset relations.

Published means a human process acknowledged the metadata version; it does not guarantee the benchmark has been externally validated.
