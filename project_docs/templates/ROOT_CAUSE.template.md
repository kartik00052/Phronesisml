# Root Cause Analysis — <issue_name>

> **File:** `docs/root_cause/<issue_name>.md` · **Date:** <date> · **ID:** <BUG-xx / ISSUE-xx / NEW-xx>

## Issue Summary
<1–3 sentences, observable symptom + impact>

## Root Cause
<the single choke point where behavior diverged from contract — not the symptom>

## Affected Components
- <module(s) + file:line>

## Affected APIs
- <public functions / classes affected>

## Affected SDK Functions
- <Phronesis methods / simple functions>

## Affected CLI
- <cli commands/flags, or "none">

## Fix Applied
- <what changed at the choke point; single source of truth rule>

## Regression Test Added
- <test name + file; must fail on pre-fix code, pass post-fix>

## Future Prevention
- <sibling sites to audit, docs to update, guard to add>
