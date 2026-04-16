# Parallel-Run Cutover Checklist

Use this checklist together with `scripts/cutover_gate.py` before deciding PyQt retirement.

## Automated Gate (Must Pass)
- [ ] `python scripts/cutover_gate.py --api-base http://127.0.0.1:8001`
- [ ] `ready_for_cutover` is `true`
- [ ] DB integrity is `ok`
- [ ] CRUD parity smoke has no count drift
- [ ] Endpoint health checks all `ok`

## Functional Manual Checks (Web)
- [ ] Alcohol create/update/delete works and persists
- [ ] Cocktail create/update/delete works and persists
- [ ] Tasting log add/delete works and persists
- [ ] Saved views add/delete persists through reload
- [ ] Tags add/remove + AND/OR filters behave correctly
- [ ] Recommendation engine returns ranked results
- [ ] AI twist assistant returns local and Groq-mode results
- [ ] Analytics dashboard loads KPI, trend, and cost insight sections

## Parallel-Run Validation (Web vs PyQt)
- [ ] Record counts align across web and PyQt for alcohol/cocktails
- [ ] Sample records match key fields in both apps
- [ ] No write conflicts observed during same-day usage window
- [ ] Backup and validation scripts completed before each release

## Decision Log
- [ ] Cutover decision documented with date/time
- [ ] Rollback command/path documented and tested
- [ ] PyQt retirement date agreed (or explicitly deferred)
