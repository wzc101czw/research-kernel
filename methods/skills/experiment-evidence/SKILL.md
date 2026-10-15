---
name: experiment-evidence
description: Create traceable experimental Run, Observation and Analysis records from a frozen research protocol and real source artifacts, separating measured results from interpretations.
---
# Experimental evidence
1. Require a Study and a *frozen* Protocol. Confirm the run corresponds to that exact protocol and published Dataset/Benchmark versions.
2. Register `science new run --title "..." --link follows PROTOCOL_ID --source SMALL_RUN_MANIFEST`; keep large trace logs and raw data in external Asset Registry rather than Git.
3. Create an Observation linked to this Run: `science new observation --title "..." --link produced_by RUN_ID --source SMALL_MEASUREMENT_MANIFEST`.
4. Create Analysis using `science new analysis --title "..." --link uses_observation OBS_ID --source SMALL_ANALYSIS_SCRIPT_OR_REPORT`.
5. Record baseline, units, uncertainty, seed, evaluation version, exclusions and negative results in sourced documents; distinguish computation success from scientific support.
6. Only after obtaining and registering real evidence, seal in order with `science seal RUN_ID --recorded-by "..."`, then `science seal OBS_ID ...`, then `science seal ANALYSIS_ID ...`. Missing evidence or an unsealed predecessor must block sealing.
7. For theoretical research, use a source-linked Analysis and a separate proof review; do not invent Run/Observation.
8. Run `python rk.py doctor`. No `verified` Claim status may be assigned by this Skill.
