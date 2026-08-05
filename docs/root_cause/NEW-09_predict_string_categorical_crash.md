# Root Cause Analysis — predict crashes on string categoricals (ETL encoding not in recipe)

> **File:** `docs/root_cause/NEW-09_predict_string_categorical_crash.md` · **Date:** 2026-08-05 · **ID:** NEW-09

## Issue Summary
`Phronesis.predict()` and `SavedRun.predict()` (restore → predict) crash with
`ValueError: could not convert string to float` whenever the dataset contains a
string categorical column. Reproduced on `BankChurners.csv` (`Existing Customer`)
and `diabetes_prediction_dataset.csv` (`Female`); datasets with all-numeric
features (e.g. `heart.csv`) pass. The model trains and explains fine — only the
raw-row prediction path fails, so the defect is invisible until the user deploys
the model.

## Root Cause
Two stages transform the data, but only one of them is replayed at prediction
time:

1. ETL (`agents/etl/agent.py:115`) calls `encode_categoricals(...)`, converting
   every string column to integers via `pd.factorize`. The resulting
   `encoding_maps` are stored only in the ETL `transform_log`, which is never
   written into `WorkflowState`.
2. Feature engineering (`agents/feature_engineering/agent.py:113`) builds the
   serializable transform recipe from **its own** log entry only
   (`build_transform_recipe(log_entry, target_column)`). Because ETL already
   encoded the strings, FE sees only numeric columns, so the recipe's
   `encoding_maps` is empty and the previously-string columns land in
   `numeric_columns` / `scaling_params`.
3. `predict()` replays the recipe via `apply_transform_recipe`
   (`ml/feature_engineering/transform.py:106-120`): with empty `encoding_maps`,
   the scaling loop runs `result[col].astype(float)` (`transform.py:116`) on the
   *raw string* value → crash.

The recipe claims to encode ("unseen labels map to 0", `transform.py:68`) but can
only do so if the encoding maps survived the ETL→FE handoff. They do not.

## Affected Components
- `phronesisml/agents/etl/agent.py:115-116` (encoding maps confined to ETL log)
- `phronesisml/agents/feature_engineering/agent.py:113` (recipe built from FE log only)
- `phronesisml/ml/feature_engineering/transform.py:106-120` (`astype(float)` on raw strings)
- `phronesisml/sdk.py:1206` (`predict`), `sdk.py:1246-1248` (`_predict_ready` recipe replay), `simple.py:1054` (`predict`)

## Affected APIs
- `Phronesis.predict`, `SavedRun.predict` (restore → predict), `simple.predict`

## Affected SDK Functions
- `Phronesis.predict`, `SavedRun.predict`, `simple.predict`/`predict_async`

## Affected CLI
- none (no CLI predict command; `train`/`run` are unaffected)

## Fix Applied
- None in this QA pass — recommended fix documented below. Not yet implemented.

### Recommended Fix (choke point)
Make the recipe a single source of truth for *all* encoding. ETL's
`encoding_maps` must reach `build_transform_recipe`. Options:

1. Persist the ETL `transform_log` (or just the `encode_categoricals` entry) into
   `WorkflowState`; have the FE agent pass it into `build_transform_recipe`, which
   merges `encoding_maps`/`categorical_columns` into the recipe (preferred —
   keeps ETL contract, minimal blast radius).
2. Or stop encoding in ETL and encode only in FE (single encoder, but a larger
   behavioural change across the ETL/validation contract).

## Regression Test Added
- None yet. Required: train on a dataset with a string categorical, then
  `predict()` raw string rows; assert no exception and that the prediction
  matches predicting on the ETL-encoded row. Must fail on pre-fix code
  (string→float ValueError) and pass post-fix.

## Future Prevention
- Any transform applied before feature engineering that changes column dtype must
  either be replayed by the recipe or recorded into `WorkflowState` and merged at
  recipe build time. Add a recipe-contract test asserting
  `apply_transform_recipe` round-trips for every dataset with ≥1 object column.
