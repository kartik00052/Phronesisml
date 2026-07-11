# Changelog

All notable changes to AetherML will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-01

### Added
- Initial release of AetherML SDK
- Multi-agent pipeline architecture with LangGraph orchestration
- Data engine abstraction (pandas, polars; Spark stubbed)
- Agents: upload, ETL, validation, EDA, target detection, feature engineering, model selection, evaluation, explainability, reporting
- AutoML: rule-based model recommendation, GridSearchCV training, metric evaluation
- SHAP-based model explainability with fallback chain
- LLM integration via GemmaClient with graceful degradation
- RAG infrastructure (Qdrant, sentence-transformers)
- Typer CLI interface
- Pydantic-based configuration system
- Comprehensive test suite for implemented agents and ML modules
