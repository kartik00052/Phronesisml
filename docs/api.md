# API Reference

## AetherML (OOP API)

The main entry point. Wraps the full LangGraph pipeline behind method-chained calls.

::: aetherml.sdk.AetherML
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

::: aetherml.sdk.DatasetSummary
::: aetherml.sdk.ValidationReport
::: aetherml.sdk.EDAReport
::: aetherml.sdk.TargetInfo
::: aetherml.sdk.FeatureReport
::: aetherml.sdk.ModelInfo
::: aetherml.sdk.EvaluationMetrics
::: aetherml.sdk.ExplanationReport

---

## Simple API

Zero-friction one-liner functions. Each runs the relevant pipeline stages and returns a frozen dataclass.

::: aetherml.simple.analyze
::: aetherml.simple.clean
::: aetherml.simple.validate
::: aetherml.simple.detect_target
::: aetherml.simple.engineer
::: aetherml.simple.select_model
::: aetherml.simple.explain
::: aetherml.simple.report
::: aetherml.simple.train

### Simple API Result Types

::: aetherml.simple.DatasetProfile
::: aetherml.simple.CleanResult
::: aetherml.simple.ValidationResult
::: aetherml.simple.TargetResult
::: aetherml.simple.FeatureResult
::: aetherml.simple.ModelResult
::: aetherml.simple.ExplainResult
::: aetherml.simple.TrainResult

---

## Advanced API

Low-level entry point for full control over pipeline stages and configuration.

::: aetherml.run_pipeline
::: aetherml.AetherMLConfig
::: aetherml.WorkflowState
