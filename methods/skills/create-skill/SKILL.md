---
name: create-skill
description: Draft and test new reusable agent workflows on user request, using the portable Agent Skills SKILL.md convention.
---
# Create a Skill

1. Obtain a concrete input/output example, task scope and success criteria.
2. Check for an existing Skill to update before introducing duplication.
3. Create a draft under `methods/skills/NAME/SKILL.md` with valid YAML `name` and `description`.
4. Keep instructions short and task-specific; place deterministic, fragile steps in tests or scripts.
5. Evaluate against a positive case, a boundary case and a failure case.
6. Show the test results and request human review before treating the Skill as published.

The Skill must not acquire broader tool permissions merely by being generated.
