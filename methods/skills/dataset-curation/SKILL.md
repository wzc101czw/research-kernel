---
name: dataset-curation
description: Register, describe and audit external research datasets without copying raw payloads into Git. Use when a researcher introduces a dataset, changes metadata or needs a reproducible data version.
---
# Dataset curation

1. Clarify dataset origin, authorized use, license, access restrictions, responsible owner and immutable version. Never infer license or permission from a file being available.
2. Keep raw files outside Git. Prefer `store://alias/frozen-file` for a local/NAS replica or a stable `s3://`, `gs://`, `oss://`, `https://` storage URI. No credentials or signed URLs in metadata.
3. Register a draft with `python rk.py asset new dataset --slug NAME --version v1 --title TITLE --owner OWNER --license LICENSE --uri URI --sha256 FULL_SHA256`.
4. Invite the researcher to modify metadata through `python rk.py asset edit dataset:NAME@v1 --reason 'review'` or `asset set ...`. Review `access`, `license`, `citation`, `extra` and physical immutability.
5. If a local file is available, bind its volume using `python rk.py store bind ALIAS --path /absolute/data/root` and verify using `python rk.py asset verify dataset:NAME@v1` (or `--file PATH`). This reads but never fetches data. State explicitly whether the checksum was only declared or actually locally verified.
6. Do not publish without human authorization. Once reviewed, human runs `asset publish ... --reviewed-by PERSON` and commits the manifest in Git.
7. For changed payload/source/license or expanded access, use `asset fork REF --version NEW --reason ...`, edit the draft, and publish a new version. When a confidentiality issue is found, immediately tighten access on the published asset via `asset set --field access --value confidential --reason ...`. Do not rewrite the published record.

For a multi-file dataset, point at a frozen archive or independently validated file-list manifest; a SHA-256 of only the manifest does NOT verify the individual data shards. DVC and bucket versioning are optional storage backends, not required by this Skill.
