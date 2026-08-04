# Root Cause Analyses

Directory for root-cause write-ups per `AI_QUALITY_GATE.md` §8 and the master charter's "AUTOMATIC ROOT CAUSE ANALYSIS".

Workflow: reproduce → isolate the boundary → classify (correctness / contract / liveness / docs-packaging) → fix at the choke point → prove with a regression test → check for siblings → record.

Use the template at `../../project_docs/templates/ROOT_CAUSE.template.md`. Name files `<issue_id>_<short_name>.md`.

Known fixed defects are summarized in `../../project_docs/Known_Issues.md` and `../../project_docs/AUDIT_REPORT.md` (BUG-01…05, ISSUE-06…08); individual RCA files are added when a write-up is produced.
