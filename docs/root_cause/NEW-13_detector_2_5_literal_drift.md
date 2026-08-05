# Root Cause Analysis — target detector "2–5 unique values" literal drift

> **File:** `docs/root_cause/NEW-13_detector_2_5_literal_drift.md` · **Date:** 2026-08-05 · **ID:** NEW-13

## Issue Summary
`phronesisml/ml/target_detection/detector.py` documents its numeric low-cardinality
branch as covering "2–5 unique values" while the executable condition covers only
`3–5` (`n_unique in range(3, 6)`); `n_unique == 2` is handled by a *separate*
later branch with a different signal name. The comment at `detector.py:305` and
the ambiguity message at `:310` ("range 2–5") both misstate the branch's true
range. Cosmetic (behaviour is still correct: 2 and 3–5 both resolve to
`ambiguous`) but it is exactly the threshold-literal-drift defect class NEW-04
documented, discovered here as a sibling site.

## Root Cause
Same pattern as NEW-04: a policy statement ("2–5") was re-typed as a range
expression (`range(3, 6)`) with an off-by-one versus the prose, and the 2-case
was split into its own branch without updating the surrounding comments/messages.
Comments and code drifted because no test asserts the branch boundaries
against the documented range.

## Affected Components
- `phronesisml/ml/target_detection/detector.py:304-344` (numeric low-cardinality branch + messages)

## Affected APIs
- none public (detector output values unchanged — both paths produce `ambiguous`)

## Affected SDK Functions
- none

## Affected CLI
- none

## Fix Applied
- None in this QA pass. Recommended: make the prose match the code — change the
  comment/message to "3–5 unique values" (or unify: single branch for
  `2 <= n_unique <= 5` with one `numeric_low_cardinality_ambiguous` signal).
  Prefer the latter so the docstring, condition, and signal name share one bound.

## Regression Test Added
- None yet. Required: a boundary test in `tests/test_target_detection.py` asserting
  the documented range (`2–5`) == handled range for numeric columns at
  `n_unique ∈ {2, 3, 4, 5}` (verify consistent task_type/signal at all four values).

## Future Prevention
- Per NEW-04 §Future Prevention: every prose range in a threshold-bearing module
  must be backed by a named constant (`MIN_AMBIGUOUS_UNIQUE`, `MAX_AMBIGUOUS_UNIQUE`)
  imported everywhere it is quoted. Grep for `2–5`, `2-5`, `range(3, 6)` after fix.
