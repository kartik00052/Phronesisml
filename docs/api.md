# API Reference

## Phronesis (OOP API)

The main entry point. Wraps the full LangGraph pipeline behind method-chained calls.

::: phronesisml.sdk.Phronesis
    options:
      show_root_heading: true
      members:
        - load
        - summary
        - clean
        - validate
        - eda
        - detect_target
        - engineer_features
        - recommend_model
        - train
        - evaluate
        - explain
        - report
        - generate_report
        - run
        - get_data
        - get_cleaned_data
        - get_features
        - get_model

### Result Types

::: phronesisml.sdk.DatasetSummary
::: phronesisml.sdk.ValidationReport
::: phronesisml.sdk.EDAReport
::: phronesisml.sdk.TargetInfo
::: phronesisml.sdk.FeatureReport
::: phronesisml.sdk.ModelInfo
::: phronesisml.sdk.EvaluationMetrics
::: phronesisml.sdk.ExplanationReport

---

## Simple API

Zero-friction one-liner functions. Each runs the relevant pipeline stages and returns a frozen dataclass.

::: phronesisml.simple.analyze
::: phronesisml.simple.clean
::: phronesisml.simple.validate
::: phronesisml.simple.detect_target
::: phronesisml.simple.engineer
::: phronesisml.simple.select_model
::: phronesisml.simple.explain
::: phronesisml.simple.report
::: phronesisml.simple.train

### Simple API Result Types

::: phronesisml.simple.DatasetProfile
::: phronesisml.simple.CleanResult
::: phronesisml.simple.ValidationResult
::: phronesisml.simple.TargetResult
::: phronesisml.simple.FeatureResult
::: phronesisml.simple.ModelResult
::: phronesisml.simple.ExplainResult
::: phronesisml.simple.TrainResult

---

## Advanced API

Low-level entry point for full control over pipeline stages and configuration.

::: phronesisml.run_pipeline
::: phronesisml.PhronesisConfig
::: phronesisml.WorkflowState
