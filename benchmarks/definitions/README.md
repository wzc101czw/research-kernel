# Evaluation Definitions

Place human-readable protocol documents and small deterministic scoring scripts here.

- `global/`: stable reusable laboratory-wide benchmarks.
- `project/`: local experimental benchmarks (promote later if useful).

A published benchmark must register its version and source file SHA-256 in `assets/registry/benchmark/` and pin any external dataset versions as relations. Changing metrics, splits or scoring implementation requires a new benchmark version. Keep raw test sets OUTSIDE Git.
