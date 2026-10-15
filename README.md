# Research Kernel Starter v0.2

A local-first, Git-native research kernel built on the Python standard library.

**[中文快速入门](QUICKSTART.zh-CN.md)** · **[科研资产与大数据管理](docs/DATA-STORAGE.zh-CN.md)** · **[Architecture](ARCHITECTURE.md)**

## Quick start

```bash
python rk.py init
python rk.py doctor
python -m unittest discover -s tests -v
```

Commit the source and metadata into Git. Raw datasets and machine-specific volume mappings are deliberately excluded by `.gitignore`.

## CLI groups

- `rk.py task new|set`, `rk.py handoff TASK_ID`, `rk.py context --task TASK_ID`
- `rk.py claim new|challenge`, `rk.py memory propose|accept`
- `rk.py asset wizard|new|list|show|edit|set|link|publish|fork|verify|check`
- `rk.py store bind|list`, `rk.py doctor`

Example: register an external dataset without downloading it:

```bash
python rk.py asset new dataset --slug demo --version v1 --title "Demo Corpus" \
  --owner "Lab" --license "unknown" --uri "s3://research-bucket/demo-v1.tar.zst"
```

Update metadata with `$EDITOR`:

```bash
python rk.py asset edit dataset:demo@v1 --reason "add citation and checksum"
```

Do not publish without verified requirements. See `docs/DATA-STORAGE.zh-CN.md` for actual review and integrity workflows.

## Installation

Requires Python >=3.10. No external Python dependencies are required. Does not connect to any model provider or storage provider by itself.

## Upgrade v0.1

Copy the new scripts and modules, merge root instructions/policies rather than overwriting local adaptations, and run `python rk.py init`. Existing task/claim/memory records remain supported; existing claim records without `asset_refs` continue to validate.

## Security caveat

The CLI is a local workflow aid, not an access-control system. Agent shell permissions and network/storage credentials must be constrained separately.
