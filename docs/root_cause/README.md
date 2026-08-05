# Root Cause Analyses

Directory for root-cause write-ups per `AI_QUALITY_GATE.md` §8 and the master charter's "AUTOMATIC ROOT CAUSE ANALYSIS".

Workflow: reproduce → isolate the boundary → classify (correctness / contract / liveness / docs-packaging) → fix at the choke point → prove with a regression test → check for siblings → record.

Use the template at `../../project_docs/templates/ROOT_CAUSE.template.md`. Name files `<issue_id>_<short_name>.md`.

Known fixed defects are summarized in `../../project_docs/Known_Issues.md` and `../../project_docs/AUDIT_REPORT.md` (BUG-01…05, ISSUE-06…08); individual RCA files are added when a write-up is produced.

## RCA index (v0.3.0 QA pass, 2026-08-05)

| ID | File | Severity | Status |
|----|------|----------|--------|
| NEW-01 | `NEW-01_evaluate_export_orphan.md` | High | Fixed (pre-pass) |
| NEW-02 | `NEW-02_composition_root_bypass.md` | High | Fixed (pre-pass) |
| NEW-03 | `NEW-03_stage_order_triplication.md` | Medium | Fixed (pre-pass) |
| NEW-04 | `NEW-04_threshold_literal_drift.md` | Medium | Fixed (pre-pass) |
| NEW-08 | `NEW-08_preflight_key_vocabulary.md` | Low | Fixed (pre-pass) |
| NEW-09 | `NEW-09_predict_string_categorical_crash.md` | High | **Confirmed, unfixed** — predict/restore→predict crashes on string categoricals (recipe omits ETL encoding maps) |
| NEW-10 | `NEW-10_cli_compare_default_crash.md` | Medium | **Confirmed, unfixed** — `compare` without `-m` crashes (`list(None)`) |
| NEW-11 | `NEW-11_resource_estimation_placeholder.md` | Low | **Confirmed, unfixed** — sampling node not wired in SDK `_run_stages`; `resource_estimation.json` placeholder |
| NEW-12 | `NEW-12_cli_missing_evaluate.md` | Low | **Confirmed, unfixed** — no `evaluate` CLI command (SDK has it) |
| NEW-13 | `NEW-13_detector_2_5_literal_drift.md` | Low | **Confirmed, unfixed** — "2–5" prose vs `range(3, 6)` code (sibling of NEW-04) |
| NEW-14 | `NEW-14_doc_drift_vs_public_surface.md` | Medium | **Confirmed, unfixed** — doc examples/counts/filenames drift vs v0.3.0 surface |

(IDs NEW-05…07 unused; NEW-09…14 written during the v0.3.0 12-phase QA pass.)
